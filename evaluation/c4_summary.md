| Campaign | Model | Domain | Runs | ME | CDA | ATC | BVC | CGP | DC | SP | CDA given exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|
| c4_m8_finance | llama3.1:8b | finance | 10 | 87.2 ± 18.2 | 63.3 ± 8.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 68.8 ± 6.6 | 97.5 ± 7.9 | 79.7 ± 11.2 |
| c4_m70_finance | llama3.3:70b | finance | 10 | 100.0 ± 0.0 | 57.7 ± 3.4 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 63.8 ± 4.0 | 90.0 ± 22.4 | 70.4 ± 7.4 |
| c4_q72_finance | qwen2.5:72b | finance | 10 | 100.0 ± 0.0 | 49.3 ± 5.3 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 68.8 ± 6.6 | 92.9 ± 18.9 | 75.0 ± 12.4 |
| c4_m8_procurement | llama3.1:8b | procurement | 10 | 100.0 ± 0.0 | 76.2 ± 17.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 100.0 ± 0.0 | 88.3 ± 13.1 |
| c4_m70_procurement | llama3.3:70b | procurement | 10 | 100.0 ± 0.0 | 77.5 ± 8.3 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 90.0 ± 21.1 | 88.0 ± 8.7 |
| c4_q72_procurement | qwen2.5:72b | procurement | 10 | 100.0 ± 0.0 | 76.8 ± 7.7 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 80.0 ± 27.4 | 92.5 ± 8.1 |

| Campaign | Sessions | Cases passed | Integrity ok | Forced blocks | Exceptions | CDA exposure | Mean s/case |
|---|---|---|---|---|---|---|---|
| c4_m8_finance | 210 | 187 | 210 | 30 | 0 | 65 of 136 (47.8 %), 61 on attempt 1 | 13.9 |
| c4_m70_finance | 210 | 197 | 210 | 9 | 0 | 32 of 85 (37.6 %), 31 on attempt 1 | 46.4 |
| c4_q72_finance | 210 | 189 | 210 | 3 | 0 | 20 of 84 (23.8 %), 19 on attempt 1 | 44.9 |
| c4_m8_procurement | 120 | 118 | 120 | 10 | 0 | 29 of 40 (72.5 %), 22 on attempt 1 | 10.0 |
| c4_m70_procurement | 120 | 118 | 120 | 14 | 0 | 50 of 74 (67.6 %), 47 on attempt 1 | 43.6 |
| c4_q72_procurement | 120 | 119 | 120 | 8 | 0 | 27 of 43 (62.8 %), 26 on attempt 1 | 49.5 |
