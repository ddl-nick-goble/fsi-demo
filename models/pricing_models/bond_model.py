import pandas as pd
import numpy as np

class Bond:
    def __init__(self, cusip, issue_date, maturity_date, coupon, frequency, face_value=100):
        self.cusip = cusip
        self.issue_date = pd.to_datetime(issue_date)
        self.maturity_date = pd.to_datetime(maturity_date)
        self.coupon_rate = float(coupon) if pd.notna(coupon) else 0.0
        self.frequency = frequency
        self.face_value = float(face_value)

        # Determine periods per year
        self.freq_per_year = 2 if frequency == 'Semi-Annual' else 1
        months = int(12 / self.freq_per_year)

        # Build cashflow dates (vector)
        dates = []
        date = self.issue_date
        while date < self.maturity_date:
            date = date + pd.DateOffset(months=months)
            dates.append(date)
        self.dates = np.array(dates)

        # Cashflow amounts (vector)
        coupon_amt = self.face_value * self.coupon_rate / 100 / self.freq_per_year
        flows = np.full(len(self.dates), coupon_amt, dtype=float)
        flows[-1] += self.face_value
        self.flows = flows

    @staticmethod
    def make_krd_shock_matrix(ttm_mat, key_tenors):
        """
        Build shock matrices for each key tenor so that each row of ttm_mat
        is shocked by 0.001 (10bps) at the key tenor with triangular/trapezoidal shape.

        key_tenors: sorted list [1,2,3,5,7,10,20,30]
        Extended endpoints at 0 and 50.
        Returns: shock_mats: array shape (len(key_tenors), *ttm_mat.shape), each entry is shock_percent (0.10) where applicable.
        """
        # decimal tenors
        ext_t = np.array([0] + key_tenors + [50], dtype=float)
        n_keys = len(key_tenors)
        shock_mats = np.zeros((n_keys,) + ttm_mat.shape, dtype=float)

        # Loop over key tenors
        for idx, kt in enumerate(key_tenors):
            # find position in ext_t
            pos = np.where(ext_t == kt)[0][0]
            t_prev = ext_t[pos-1]
            t_next = ext_t[pos+1]

            if pos == 1:
                # First key tenor trapezoid: flat from 0 to kt, ramp down to 0 at t_next
                shock = np.where(ttm_mat <= kt, 1.0, 
                                 np.where(ttm_mat < t_next, (t_next - ttm_mat)/(t_next - kt), 0.0))
            elif pos == len(ext_t)-2:
                # Last key tenor trapezoid: flat from kt to inf, ramp from 0 at t_prev to 1 at kt
                shock = np.where(ttm_mat >= kt, 1.0,
                                 np.where(ttm_mat > t_prev, (ttm_mat - t_prev)/(kt - t_prev), 0.0))
            else:
                # Triangle: ramp up from t_prev to kt, down from kt to t_next
                shock = np.where((ttm_mat >= t_prev) & (ttm_mat <= kt),
                                 (ttm_mat - t_prev)/(kt - t_prev),
                                 np.where((ttm_mat > kt) & (ttm_mat <= t_next),
                                          (t_next - ttm_mat)/(t_next - kt),
                                          0.0))
            # scale to 10bps in percent form
            shock_mats[idx] = shock * 0.10  # 0.10% = 10bps
        return shock_mats

    @classmethod
    def price_batch_with_sensitivities(cls, bonds, as_of_date, yield_curve):
        """
        Vectorized pricing for multiple Bond instances, computing:
          - price
          - dv01 (parallel 10bp shock)
          - krd at tenors [1,2,3,5,7,10,20,30]

        Returns tuple (pvs, dv01s, krds_matrix) where:
          pvs: shape (n,)
          dv01s: shape (n,) = PV_base - PV_parallel
          krds_matrix: shape (n, n_keys)
        """
        ao = pd.to_datetime(as_of_date)
        n = len(bonds)
        # determine max cashflow length
        max_cf = max(len(b.dates) for b in bonds)
        flows_mat = np.zeros((n, max_cf), dtype=float)
        ttm_mat = np.zeros((n, max_cf), dtype=float)

        for i, b in enumerate(bonds):
            k = len(b.dates)
            ttm = (b.dates.astype('datetime64[D]') - ao.to_datetime64()) / np.timedelta64(1, 'D') / 365.25
            ttm = np.where(ttm < 0.0, 0.0, ttm)
            flows_mat[i, :k] = b.flows
            ttm_mat[i, :k] = ttm

        # base rates in percent
        rates_pct = yield_curve(ttm_mat)
        # discount factors base
        dfs_base = np.exp(-(rates_pct/100) * ttm_mat)
        pvs_base = (flows_mat * dfs_base).sum(axis=1)

        # parallel shock: add 0.10% to all rates
        dfs_par = np.exp(-((rates_pct + 0.10)/100) * ttm_mat)
        pvs_par = (flows_mat * dfs_par).sum(axis=1)
        dv01 = pvs_base - pvs_par

        # key tenors
        key_tenors = [1,2,3,5,7,10,20,30]
        shock_mats = cls.make_krd_shock_matrix(ttm_mat, key_tenors)
        n_keys = len(key_tenors)
        krds = np.zeros((n, n_keys), dtype=float)
        for idx in range(n_keys):
            # combine base rates with key shock
            shock_pct = shock_mats[idx]
            dfs_k = np.exp(-((rates_pct + shock_pct)/100) * ttm_mat)
            pvs_k = (flows_mat * dfs_k).sum(axis=1)
            krds[:, idx] = pvs_base - pvs_k

        return pvs_base, dv01, krds