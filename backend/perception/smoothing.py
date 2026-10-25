import math


class OneEuroFilter:
    def __init__(self, t0, x0, min_cutoff=1.0, beta=0.0, d_cutoff=1.0):
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)
        self.x_prev = x0
        self.dx_prev = self._zero_like(x0)
        self.t_prev = float(t0)

    @staticmethod
    def _zero_like(val):
        if isinstance(val, (list, tuple)):
            return [0.0] * len(val)
        return 0.0

    @staticmethod
    def smoothing_factor(t_e, cutoff):
        r = 2 * math.pi * cutoff * t_e
        return r / (r + 1)

    @staticmethod
    def exponential_smoothing(a, x, x_prev):
        if isinstance(x, (list, tuple)):
            return [a * xi + (1 - a) * xp for xi, xp in zip(x, x_prev)]
        return a * x + (1 - a) * x_prev

    def __call__(self, t, x):
        t_e = t - self.t_prev
        if t_e <= 0.0:
            return self.x_prev

        if isinstance(x, (list, tuple)):
            dx = [(xi - xp) / t_e for xi, xp in zip(x, self.x_prev)]
        else:
            dx = (x - self.x_prev) / t_e

        a_d = self.smoothing_factor(t_e, self.d_cutoff)
        dx_hat = self.exponential_smoothing(a_d, dx, self.dx_prev)

        if isinstance(x, (list, tuple)):
            speed = math.sqrt(sum(v ** 2 for v in dx_hat))
            cutoff = self.min_cutoff + self.beta * speed
        else:
            cutoff = self.min_cutoff + self.beta * abs(dx_hat)

        a = self.smoothing_factor(t_e, cutoff)
        x_hat = self.exponential_smoothing(a, x, self.x_prev)

        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat
