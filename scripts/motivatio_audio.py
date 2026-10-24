"""Son MOTIVATIO : musique lo-fi et bruitages, entièrement générés par calcul (aucun droit d'auteur)."""
import numpy as np

SR = 44100


def _env(n, attaque, chute):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(attaque, 1e-4)) * np.exp(-t / max(chute, 1e-4))


def _passe_bas(x, alpha):
    """Filtre passe-bas d'ordre 1 (vectorisé par blocs via cumsum exponentiel approché)."""
    y = np.empty_like(x); acc = 0.0
    for i in range(0, len(x), 4096):
        bloc = x[i:i + 4096]
        out = np.empty_like(bloc)
        for j, v in enumerate(bloc):
            acc += alpha * (v - acc); out[j] = acc
        y[i:i + 4096] = out
    return y


def _lisse(x, n):
    if n <= 1:
        return x
    k = np.ones(n) / n
    return np.convolve(x, k, mode="same")


def _bruit(n, rng):
    return rng.standard_normal(n)


# ---------------- musique ----------------
PROGRESSIONS = [
    # accords en Hz (fondamentale grave + accord), 1 accord par mesure
    [(110.00, [220.00, 261.63, 329.63, 392.00]), (87.31, [174.61, 220.00, 261.63, 329.63]),
     (130.81, [261.63, 329.63, 392.00, 493.88]), (98.00, [196.00, 246.94, 293.66, 369.99])],
    [(146.83, [293.66, 349.23, 440.00, 523.25]), (98.00, [196.00, 246.94, 293.66, 349.23]),
     (130.81, [261.63, 329.63, 392.00, 493.88]), (110.00, [220.00, 261.63, 329.63, 392.00])],
    [(130.81, [261.63, 311.13, 392.00, 466.16]), (103.83, [207.65, 261.63, 311.13, 392.00]),
     (116.54, [233.08, 293.66, 349.23, 440.00]), (98.00, [196.00, 246.94, 293.66, 349.23])],
]


def musique(duree, graine=0, bpm=88):
    rng = np.random.default_rng(graine)
    n = int(duree * SR) + SR
    out = np.zeros(n)
    beat = 60 / bpm
    mesure = beat * 4
    prog = PROGRESSIONS[graine % len(PROGRESSIONS)]
    nb_mesures = int(duree / mesure) + 2
    for m in range(nb_mesures):
        t0 = m * mesure
        basse, accord = prog[m % len(prog)]
        # piano électrique doux : deux attaques par mesure
        for frappe, vel in ((0.0, 1.0), (beat * 2.5, 0.55)):
            i0 = int((t0 + frappe) * SR)
            if i0 >= n: continue
            l = min(int(mesure * SR), n - i0)
            t = np.arange(l) / SR
            env = _env(l, 0.01, 1.4) * vel
            trem = 1 + 0.08 * np.sin(2 * np.pi * 4.5 * t)
            s = np.zeros(l)
            for f in accord:
                det = f * (1 + rng.uniform(-0.002, 0.002))
                s += np.sin(2 * np.pi * det * t) + 0.25 * np.sin(4 * np.pi * det * t) * np.exp(-t * 3)
            out[i0:i0 + l] += 0.05 * s * env * trem
        # basse
        for frappe in (0.0, beat * 1.5, beat * 2.5):
            i0 = int((t0 + frappe) * SR)
            if i0 >= n: continue
            l = min(int(beat * 1.2 * SR), n - i0)
            t = np.arange(l) / SR
            s = np.tanh(1.6 * np.sin(2 * np.pi * basse * t))
            out[i0:i0 + l] += 0.16 * s * _env(l, 0.008, 0.35)
        # batterie
        for b in range(4):
            tb = t0 + b * beat
            # grosse caisse temps 1 et 3 (+ contretemps léger)
            if b in (0, 2) or (b == 3 and m % 2):
                i0 = int((tb + (beat * 0.5 if b == 3 else 0)) * SR)
                if i0 < n:
                    l = min(int(0.32 * SR), n - i0); t = np.arange(l) / SR
                    f = 48 + 70 * np.exp(-t * 28)
                    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(l, 0.002, 0.16)
                    out[i0:i0 + l] += 0.42 * s * (0.6 if b == 3 else 1)
            # caisse claire temps 2 et 4
            if b in (1, 3):
                i0 = int(tb * SR)
                if i0 < n:
                    l = min(int(0.22 * SR), n - i0)
                    nz = _bruit(l, rng); nz = nz - _lisse(nz, 6)
                    t = np.arange(l) / SR
                    s = 0.6 * nz * _env(l, 0.001, 0.07) + 0.4 * np.sin(2 * np.pi * 190 * t) * _env(l, 0.001, 0.05)
                    out[i0:i0 + l] += 0.16 * s
            # charleston en croches, légèrement swingué
            for c, vel in ((0.0, 1.0), (0.58, 0.6)):
                i0 = int((tb + c * beat) * SR)
                if i0 < n:
                    l = min(int(0.06 * SR), n - i0)
                    nz = _bruit(l, rng); nz = nz - _lisse(nz, 3)
                    out[i0:i0 + l] += 0.05 * vel * nz * _env(l, 0.001, 0.018)
    # couleur lo-fi : léger passe-bas et craquements
    out = 0.75 * out + 0.25 * _lisse(out, 5)
    crac = np.zeros(n); pos = rng.integers(0, n, int(duree * 7))
    crac[pos] = rng.uniform(-0.05, 0.05, len(pos))
    out += crac
    out = out[:int(duree * SR)]
    t = np.arange(len(out)) / SR
    out *= np.minimum(1, t / 0.4) * np.minimum(1, (duree - t) / 1.2)
    return (out / max(1e-6, np.abs(out).max()) * 0.8).astype(np.float32)


# ---------------- bruitages ----------------
def _whoosh(rng):
    l = int(0.42 * SR); t = np.arange(l) / SR
    nz = _bruit(l, rng)
    bas = _lisse(nz, 18); haut = nz - _lisse(nz, 3)
    mix = np.sin(np.pi * t / t[-1]) ** 2
    s = (bas * (1 - t / t[-1]) + haut * (t / t[-1]) * 0.5) * mix
    return 0.55 * s / np.abs(s).max()


def _pop(rng, f0=740):
    l = int(0.11 * SR); t = np.arange(l) / SR
    f = f0 * (1 - 0.45 * t / t[-1])
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(l, 0.002, 0.035)
    return 0.45 * s


def _tick(rng):
    l = int(0.012 * SR)
    nz = _bruit(l, rng); nz = nz - _lisse(nz, 2)
    return 0.12 * rng.uniform(0.6, 1.0) * nz * _env(l, 0.0005, 0.004)


def _ding(rng):
    l = int(0.7 * SR); t = np.arange(l) / SR
    s = (np.sin(2 * np.pi * 1318.5 * t) + 0.6 * np.sin(2 * np.pi * 1975.5 * t) * np.exp(-t * 4)) * _env(l, 0.003, 0.28)
    return 0.22 * s


def _erreur(rng):
    out = np.zeros(int(0.32 * SR))
    for k in (0, 1):
        l = int(0.1 * SR); t = np.arange(l) / SR
        s = np.tanh(3 * np.sin(2 * np.pi * 196 * t)) * _env(l, 0.004, 0.05)
        i0 = int(k * 0.14 * SR); out[i0:i0 + l] += 0.2 * s
    return out


def _brillance(rng):
    out = np.zeros(int(0.8 * SR))
    for k in range(6):
        l = int(0.25 * SR); t = np.arange(l) / SR
        f = rng.uniform(2200, 3600)
        s = np.sin(2 * np.pi * f * t) * _env(l, 0.002, 0.06)
        i0 = int(k * 0.09 * SR); out[i0:i0 + l] += 0.07 * s
    return out


GENERATEURS = {"whoosh": _whoosh, "pop": _pop, "tick": _tick, "ding": _ding, "erreur": _erreur, "brillance": _brillance}


def bruitages(duree, evenements, graine=0):
    """evenements : liste de (temps_s, type). Retourne la piste de bruitages."""
    rng = np.random.default_rng(graine + 7)
    out = np.zeros(int(duree * SR) + SR)
    for t, typ in evenements:
        s = GENERATEURS[typ](rng)
        i0 = int(max(0, t) * SR)
        if i0 >= len(out): continue
        l = min(len(s), len(out) - i0)
        out[i0:i0 + l] += s[:l]
    return np.clip(out[:int(duree * SR)], -1, 1).astype(np.float32)
