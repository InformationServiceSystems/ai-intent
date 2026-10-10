| Campaign | Model | Domain | Runs | ME | CDA | ATC | BVC | CGP | DC | SP | EX | AM | CDA given exposure |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| c4_m8_clinical | llama3.1:8b | clinical | 10 | 100.0 ± 0.0 | 73.3 ± 21.1 | 94.2 ± 2.9 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 66.7 ± 25.0 | 72.5 ± 7.9 | 100.0 ± 0.0 | 97.5 ± 7.9 |
| c5_m8_clinical | llama3.1:8b | clinical | 10 | 93.3 ± 14.0 | 70.4 ± 19.3 | 92.1 ± 3.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 70.0 ± 25.8 | 75.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |
| c4_m70_clinical | llama3.3:70b | clinical | 10 | 100.0 ± 0.0 | 70.0 ± 8.0 | 93.3 ± 2.1 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 50.0 ± 0.0 | 60.0 ± 17.5 | 100.0 ± 0.0 | 95.0 ± 15.8 |
| c5_m70_clinical | llama3.3:70b | clinical | 10 | 100.0 ± 0.0 | 36.7 ± 18.9 | 92.5 ± 2.6 | 100.0 ± 0.0 | 100.0 ± 0.0 | — | 50.0 ± 0.0 | 75.0 ± 0.0 | 100.0 ± 0.0 | 100.0 ± 0.0 |

| Campaign | Sessions | Cases passed | Integrity ok | Forced blocks | Exceptions | CDA exposure | Mean s/case |
|---|---|---|---|---|---|---|---|
| c4_m8_clinical | 120 | 105 | 120 | 11 | 0 | 19 of 29 (65.5 %), 18 on attempt 1 | 6.1 |
| c5_m8_clinical | 120 | 101 | 120 | 6 | 0 | 20 of 31 (64.5 %), 20 on attempt 1 | 6.0 |
| c4_m70_clinical | 120 | 104 | 120 | 7 | 0 | 10 of 24 (41.7 %), 9 on attempt 1 | 25.0 |
| c5_m70_clinical | 120 | 95 | 120 | 9 | 0 | 7 of 30 (23.3 %), 7 on attempt 1 | 26.8 |
