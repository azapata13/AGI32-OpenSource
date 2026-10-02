"""Photometry: IES LM-63 parsing and generic distributions.

Every distribution is normalised to a total flux of 1 (per unit of PPF). The engine multiplies
by the fixture PPF (µmol/s), so intensities come out in µmol/s/sr whatever the units used in
the IES file (lumens or µmol). This mirrors the common practice of overriding the "lumens"
field with the fixture PPF.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


class Distribution:
    """Luminous (photon) intensity per unit flux, I(theta, phi) in 1/sr.

    theta: angle from nadir (0 = straight down), radians.
    phi:   azimuth around the fixture axis, radians (0 = along fixture length / +X).
    """

    def intensity(self, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError


@dataclass
class CosinePower(Distribution):
    """Rotationally symmetric I(theta) = I0 cos^n(theta), downward hemisphere only."""

    n: float = 1.0

    def intensity(self, theta, phi):
        c = np.clip(np.cos(theta), 0.0, None)
        i0 = (self.n + 1.0) / (2.0 * np.pi)  # flux of I0 cos^n over the hemisphere = 2pi I0/(n+1)
        return i0 * c ** self.n


class Batwing(Distribution):
    """Wide 'flat-field' distribution typical of horticultural toplights (WD optics).

    Inside the half-angle `cutoff`, I(theta) is proportional to 1/cos^p(theta), which spreads
    light toward the edges (p = 3 would give a perfectly flat field on a plane). Beyond the
    cutoff the intensity rolls off smoothly to zero at the horizon.
    """

    def __init__(self, beam_angle_deg: float = 120.0, p: float = 1.5):
        self.cut = np.radians(min(max(beam_angle_deg, 20.0), 170.0) / 2)
        self.p = p
        th = np.linspace(0, np.pi / 2, 2001)
        raw = self._shape(th)
        self.k = 1.0 / float(np.trapezoid(raw * np.sin(th) * 2 * np.pi, th))

    def _shape(self, theta):
        theta = np.asarray(theta, dtype=float)
        inside = 1.0 / np.maximum(np.cos(np.minimum(theta, self.cut)), 1e-3) ** self.p
        edge = 1.0 / max(np.cos(self.cut), 1e-3) ** self.p
        span = max(np.pi / 2 - self.cut, 1e-3)
        roll = edge * np.cos(np.clip((theta - self.cut) / span, 0, 1) * np.pi / 2) ** 2
        out = np.where(theta <= self.cut, inside, roll)
        return np.where(theta < np.pi / 2, out, 0.0)

    def intensity(self, theta, phi):
        return self.k * self._shape(theta)


class TabulatedDistribution(Distribution):
    """Intensity tabulated on C-planes between 0 and 90 deg (quadrant symmetry).

    `planes` maps the C angle in degrees (0 = along the fixture length) to intensities at
    `angles_deg` from nadir. With only the 0 and 90 planes, the two are blended as
    I0 cos^2(phi) + I90 sin^2(phi); with more planes, linearly in phi. Normalised to a flux of 1.
    """

    def __init__(self, angles_deg, planes: dict):
        self.a = np.radians(np.asarray(angles_deg, dtype=float))
        items = sorted((float(k), np.asarray(v, dtype=float)) for k, v in planes.items())
        self.c = np.radians([k for k, _ in items])
        self.I = np.array([v for _, v in items])
        if self.I.shape[1] != len(self.a):
            raise ValueError("Tabulated photometry: each plane needs one value per angle.")
        if len(self.c) == 1:
            self.c, self.I = np.radians([0.0, 90.0]), np.vstack([self.I, self.I])
        if not (np.isclose(self.c[0], 0) and np.isclose(self.c[-1], np.pi / 2)):
            raise ValueError("Tabulated photometry: planes must start at 0 and end at 90 deg.")
        self.two_planes = len(self.c) == 2
        th = np.linspace(0, np.pi / 2, 721)
        ph = np.linspace(0, 2 * np.pi, 361)
        T, P = np.meshgrid(th, ph, indexing="ij")
        flux = np.trapezoid(np.trapezoid(self._raw(T, P) * np.sin(T), ph, axis=1), th)
        self.k = 1.0 / float(flux)

    def _raw(self, theta, phi):
        theta = np.asarray(theta, dtype=float)
        phi = np.mod(np.broadcast_to(np.asarray(phi, dtype=float), theta.shape), np.pi)
        phi = np.where(phi > np.pi / 2, np.pi - phi, phi)  # fold to [0, 90 deg]
        per_plane = np.array([np.interp(theta, self.a, row, right=0.0) for row in self.I])
        if self.two_planes:
            c2 = np.cos(phi) ** 2
            out = per_plane[0] * c2 + per_plane[1] * (1 - c2)
        else:
            i = np.clip(np.searchsorted(self.c, phi) - 1, 0, len(self.c) - 2)
            t = (phi - self.c[i]) / (self.c[i + 1] - self.c[i])
            lo = np.take_along_axis(per_plane, i[None], 0)[0]
            hi = np.take_along_axis(per_plane, (i + 1)[None], 0)[0]
            out = lo * (1 - t) + hi * t
        return np.where(theta < np.pi / 2, out, 0.0)

    def intensity(self, theta, phi):
        return self.k * self._raw(theta, phi)


class IESDistribution(Distribution):
    def __init__(self, vertical: np.ndarray, horizontal: np.ndarray, candela: np.ndarray,
                 width: float = 0.0, length: float = 0.0, header: dict | None = None):
        self.v = np.radians(vertical)
        self.h = np.radians(horizontal)
        self.cd = candela  # shape (n_h, n_v)
        self.width = width
        self.length = length
        self.header = header or {}
        self.cd = self.cd / self._total_flux()

    # -------------------------------------------------------------- symmetry
    def _fold_phi(self, phi: np.ndarray) -> np.ndarray:
        h_max = self.h[-1] if len(self.h) else 0.0
        phi = np.mod(phi, 2 * np.pi)
        if len(self.h) == 1:  # full rotational symmetry
            return np.zeros_like(phi)
        if np.isclose(h_max, np.pi / 2):  # quadrant symmetry
            phi = np.where(phi > np.pi, 2 * np.pi - phi, phi)
            return np.where(phi > np.pi / 2, np.pi - phi, phi)
        if np.isclose(h_max, np.pi):  # bilateral symmetry about the 0-180 plane
            return np.where(phi > np.pi, 2 * np.pi - phi, phi)
        return phi  # full 0-360 data

    def _raw(self, theta, phi):
        phi = self._fold_phi(np.asarray(phi, dtype=float))
        theta = np.asarray(theta, dtype=float)
        if len(self.h) == 1:
            return np.interp(theta, self.v, self.cd[0], left=self.cd[0, 0], right=0.0)
        # bilinear on (h, v)
        hi = np.clip(np.searchsorted(self.h, phi) - 1, 0, len(self.h) - 2)
        h0, h1 = self.h[hi], self.h[hi + 1]
        t = np.where(h1 > h0, (phi - h0) / (h1 - h0), 0.0)
        out = np.empty_like(theta)
        flat_theta, flat_hi, flat_t = theta.ravel(), hi.ravel(), t.ravel()
        res = out.ravel()
        for k in np.unique(flat_hi):
            m = flat_hi == k
            a = np.interp(flat_theta[m], self.v, self.cd[k], right=0.0)
            b = np.interp(flat_theta[m], self.v, self.cd[k + 1], right=0.0)
            res[m] = a * (1 - flat_t[m]) + b * flat_t[m]
        return res.reshape(theta.shape)

    def _total_flux(self) -> float:
        th = np.linspace(0, np.pi, 361)
        ph = np.linspace(0, 2 * np.pi, 145)
        T, P = np.meshgrid(th, ph, indexing="ij")
        self.cd = self.cd.astype(float)
        I = self._raw(T, P)
        integrand = I * np.sin(T)
        return float(np.trapezoid(np.trapezoid(integrand, ph, axis=1), th))

    def intensity(self, theta, phi):
        return self._raw(theta, phi)


def parse_ies(path: str | Path) -> IESDistribution:
    """Parse an IES LM-63 file (1986, 1991, 1995, 2002, 2019 variants, type C photometry)."""
    text = Path(path).read_text(encoding="latin-1", errors="replace")
    lines = text.splitlines()
    header: dict[str, str] = {}
    idx = 0
    for idx, line in enumerate(lines):
        s = line.strip()
        if s.startswith("[") and "]" in s:
            key, _, val = s[1:].partition("]")
            header[key.strip().upper()] = val.strip()
        if s.upper().startswith("TILT"):
            break
    else:
        raise ValueError(f"{path}: no TILT line found, not an IES file.")
    tilt = lines[idx].split("=", 1)[1].strip().upper()
    rest = " ".join(lines[idx + 1:]).replace(",", " ").split()
    pos = 0
    if tilt == "INCLUDE":
        pos += 1  # lamp-to-luminaire geometry
        n_tilt = int(float(rest[pos])); pos += 1
        pos += 2 * n_tilt
    nums = [float(x) for x in rest[pos:]]
    (n_lamps, lumens_per_lamp, multiplier, n_v, n_h, photometric_type, units,
     width, length, height) = nums[:10]
    _ballast, _future, input_watts = nums[10:13]
    p = 13
    n_v, n_h = int(n_v), int(n_h)
    vertical = np.array(nums[p:p + n_v]); p += n_v
    horizontal = np.array(nums[p:p + n_h]); p += n_h
    cd = np.array(nums[p:p + n_v * n_h]).reshape(n_h, n_v) * multiplier
    if int(photometric_type) != 1:
        raise ValueError(f"{path}: only type C photometry is supported.")
    scale = 0.3048 if int(units) == 1 else 1.0
    header.update({"_input_watts": str(input_watts), "_lumens": str(n_lamps * lumens_per_lamp)})
    return IESDistribution(vertical, horizontal, cd, abs(width) * scale, abs(length) * scale, header)
