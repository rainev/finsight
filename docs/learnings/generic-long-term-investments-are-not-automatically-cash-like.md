---
name: generic-long-term-investments-are-not-automatically-cash-like
description: LongTermInvestments may sit in other assets and contain non-marketable holdings, so its label alone cannot add the balance to excess cash.
metadata: { type: gotcha }
---
The generic marketable-securities alias initially added ROK and MCO
`LongTermInvestments` to cash even though their retained models excluded those
balances and the current filings place them in other assets.

An issuer rule may exclude the generic balance only when the current complete
structural filing proves its placement or component scope and no approved
marketable-security fact conflicts. Keep directly reported short-term cash-like
investments. Fail closed when a future filing changes the presentation.
