## models/pricing_models/bond_model.py
import pandas as pd
import numpy as np

class Bond:
    def __init__(self, cusip, issue_date, maturity_date, coupon, frequency, price, face_value=100):
        self.cusip = cusip
        self.issue_date = pd.to_datetime(issue_date)
        self.maturity_date = pd.to_datetime(maturity_date)
        self.coupon_rate = float(coupon) if pd.notna(coupon) else 0.0
        self.frequency = frequency
        self.face_value = float(face_value)

        # Determine periods per year
        self.freq_per_year = 2 if frequency == 'Semi-Annual' else 1
        months = int(12 / self.freq_per_year)

        # Build cashflow dates
        dates = []
        date = self.issue_date
        while date < self.maturity_date:
            date = date + pd.DateOffset(months=months)
            dates.append(date)
        self.dates = np.array(dates)

        # Cashflow amounts
        coupon_amt = self.face_value * self.coupon_rate / 100 / self.freq_per_year
        flows = np.full(len(self.dates), coupon_amt, dtype=float)
        flows[-1] += self.face_value
        self.flows = flows

