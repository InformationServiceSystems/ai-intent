| Campaign | Model | Domain | Runs | ME | CDA | ATC | BVC | CGP | DC | SP | EX | AM | CDA given exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fin_m8_finance | llama3.1:8b | finance | 10 | 84.3 ± 8.9 | 62.9 ± 10.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 63.8 ± 4.0 | 97.5 ± 7.9 | — | — | 84.5 ± 9.7 |
| fin_m70_finance | llama3.3:70b | finance | 10 | 100.0 ± 0.0 | 57.5 ± 6.8 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 61.2 ± 7.1 | 85.7 ± 24.4 | — | — | 73.3 ± 7.9 |
| fin_q72_finance | qwen2.5:72b | finance | 10 | 100.0 ± 0.0 | 48.6 ± 4.9 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 72.5 ± 5.3 | 96.9 ± 8.8 | — | — | 73.3 ± 3.5 |
| fin_m8_procurement | llama3.1:8b | procurement | 10 | 100.0 ± 0.0 | 65.1 ± 19.4 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 100.0 ± 0.0 | — | — | 90.3 ± 12.8 |
| fin_m70_procurement | llama3.3:70b | procurement | 10 | 100.0 ± 0.0 | 77.5 ± 5.2 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 80.0 ± 25.8 | — | — | 88.0 ± 8.1 |
| fin_q72_procurement | qwen2.5:72b | procurement | 10 | 100.0 ± 0.0 | 67.8 ± 11.9 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | 50.0 ± 0.0 | 88.9 ± 22.0 | — | — | 79.3 ± 8.8 |
| fin_m8_clinical | llama3.1:8b | clinical | 10 | 96.7 ± 10.5 | 66.3 ± 20.8 | 98.3 ± 2.2 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 60.0 ± 21.1 | 82.5 ± 12.1 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| fin_m70_clinical | llama3.3:70b | clinical | 10 | 100.0 ± 0.0 | 43.3 ± 8.6 | 99.6 ± 1.3 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 50.0 ± 0.0 | 95.0 ± 10.5 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| fin_q72_clinical | qwen2.5:72b | clinical | 10 | 100.0 ± 0.0 | 35.0 ± 20.4 | 100.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 55.0 ± 15.8 | 91.2 ± 11.9 | 100.0 ± 0.0 | 100.0 ± 0.0 |

| Campaign | Sessions | Infrastructure errors | Cases passed | Integrity ok | Forced blocks | Exceptions | CDA exposure | Mean s/case |
|---|---|---|---|---|---|---|---|---|
| fin_m8_finance | 210 | 0 | 183 | 210 | 25 | 0 | 52 of 124 (41.9 %), 50 on attempt 1 | 23.2 |
| fin_m70_finance | 210 | 0 | 192 | 210 | 8 | 0 | 35 of 87 (40.2 %), 34 on attempt 1 | 45.1 |
| fin_q72_finance | 210 | 0 | 188 | 210 | 5 | 0 | 22 of 84 (26.2 %), 20 on attempt 1 | 43.8 |
| fin_m8_procurement | 120 | 0 | 115 | 120 | 3 | 0 | 22 of 39 (56.4 %), 20 on attempt 1 | 23.3 |
| fin_m70_procurement | 120 | 0 | 118 | 120 | 15 | 0 | 50 of 72 (69.4 %), 48 on attempt 1 | 45.9 |
| fin_q72_procurement | 120 | 0 | 117 | 120 | 9 | 0 | 34 of 58 (58.6 %), 30 on attempt 1 | 56.8 |
| fin_m8_clinical | 120 | 0 | 103 | 120 | 9 | 0 | 18 of 29 (62.1 %), 18 on attempt 1 | 6.9 |
| fin_m70_clinical | 120 | 0 | 105 | 120 | 8 | 0 | 9 of 30 (30.0 %), 9 on attempt 1 | 25.3 |
| fin_q72_clinical | 120 | 0 | 100 | 120 | 6 | 0 | 7 of 32 (21.9 %), 7 on attempt 1 | 27.9 |
