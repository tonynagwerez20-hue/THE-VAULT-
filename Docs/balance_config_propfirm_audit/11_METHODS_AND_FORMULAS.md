# 11 — MATHEMATICAL METHODS AND FORMULAS

## 1. Intended Risk Budget
$$\text{RiskBudget} = \text{Balance} \times \text{IntendedRiskPct}$$

## 2. Minimum Executable Lot Sizing
$$\text{IdealVolume} = \frac{\text{RiskBudget}}{\text{StopDistance} \times \text{ContractSize}}$$
$$\text{ActualVolume} = \max\left(0.01, \lfloor \text{IdealVolume} / 0.01 \rfloor \times 0.01\right)$$

## 3. Minimum-Lot Risk Distortion
$$\text{RiskDistortion} = \frac{\text{ActualRiskPct}}{\text{IntendedRiskPct}}$$
