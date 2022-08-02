;; original sequence 1: (1 8 2 3 4 5 29 30 31 32 33 34 35 36 -56 -55 -54 -53 -52 -51 -50 -28 -27 -26 9 -49 -48 -47 -46 -45 41 42 43 44 37 38 39 40 16 17 18 19 20 21 22 23 24 25 10 11 12 13 14 15 57 58 59 6 7 60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95 96 -105 -104 -103 -102 -101 -100 -99 -98 -97)
;; original sequence 2: (1 2 3 4 5 6 7 8 9 10 49 50 51 52 53 28 29 30 31 32 33 34 35 -40 -39 -38 -37 -60 -59 -58 -57 -56 11 12 13 14 15 -76 -75 -74 -73 -72 -71 -70 -69 -68 -67 -66 -65 -64 -63 -62 -61 -27 -26 -44 -43 -42 -41 45 46 47 48 -36 54 -25 -24 -23 -22 -21 -20 -19 -18 -17 -16 -90 -89 -88 -87 -86 -85 77 78 79 80 81 82 83 84 91 92 93 94 95 96 -55 -105 -104 -103 -102 -101 -100 -99 -98 -97)
;; simplified sequence 1: (1 8 115 111 36 -56 -55 -54 117 -28 120 9 -49 110 116 107 10 114 118 119 60 106 109 113 112 108)
;; simplified sequence 2: (1 115 119 8 9 10 49 -117 28 111 -116 -60 -118 -56 114 -106 120 -110 -36 54 -107 -113 109 112 -55 108)
;; common subsequences: (((61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76) . 106) ((16 17 18 19 20 21 22 23 24 25) . 107) ((-105 -104 -103 -102 -101 -100 -99 -98 -97) . 108) ((77 78 79 80 81 82 83 84) . 109) ((-48 -47 -46 -45 41 42 43 44) . 110) ((29 30 31 32 33 34 35) . 111) ((91 92 93 94 95 96) . 112) ((85 86 87 88 89 90) . 113) ((11 12 13 14 15) . 114) ((2 3 4 5) . 115) ((37 38 39 40) . 116) ((-53 -52 -51 -50) . 117) ((57 58 59) . 118) ((6 7) . 119) ((-27 -26) . 120))
;; #safe insertions/deletions: 0
;; sequence 1 (names): ((NORMAL G1) (NORMAL G8) (NORMAL SUB10) (NORMAL SUB6) (NORMAL G36) (INVERTED G56) (INVERTED G55) (INVERTED G54) (NORMAL SUB12) (INVERTED G28) (NORMAL SUB15) (NORMAL G9) (INVERTED G49) (NORMAL SUB5) (NORMAL SUB11) (NORMAL SUB2) (NORMAL G10) (NORMAL SUB9) (NORMAL SUB13) (NORMAL SUB14) (NORMAL G60) (NORMAL SUB1) (NORMAL SUB4) (NORMAL SUB8) (NORMAL SUB7) (NORMAL SUB3))
;; sequence 2 (names): ((NORMAL G1) (NORMAL SUB10) (NORMAL SUB14) (NORMAL G8) (NORMAL G9) (NORMAL G10) (NORMAL G49) (INVERTED SUB12) (NORMAL G28) (NORMAL SUB6) (INVERTED SUB11) (INVERTED G60) (INVERTED SUB13) (INVERTED G56) (NORMAL SUB9) (INVERTED SUB1) (NORMAL SUB15) (INVERTED SUB5) (INVERTED G36) (NORMAL G54) (INVERTED SUB2) (INVERTED SUB8) (NORMAL SUB4) (NORMAL SUB7) (INVERTED G55) (NORMAL SUB3))

(DEFINE (PROBLEM PLATYCODON-TO-MERCIERA) (:DOMAIN GENOME-EDIT-DISTANCE)
        (:OBJECTS SUB15 SUB14 SUB13 SUB12 SUB11 SUB10 SUB9 SUB8 SUB7
            SUB6 SUB5 SUB4 SUB3 SUB2 SUB1 G60 G56 G55 G54 G49 G36 G28
            G10 G9 G8 G1)
        (:INIT (NORMAL G1) (NORMAL G8) (NORMAL SUB10) (NORMAL SUB6)
               (NORMAL G36) (INVERTED G56) (INVERTED G55)
               (INVERTED G54) (NORMAL SUB12) (INVERTED G28)
               (NORMAL SUB15) (NORMAL G9) (INVERTED G49) (NORMAL SUB5)
               (NORMAL SUB11) (NORMAL SUB2) (NORMAL G10) (NORMAL SUB9)
               (NORMAL SUB13) (NORMAL SUB14) (NORMAL G60) (NORMAL SUB1)
               (NORMAL SUB4) (NORMAL SUB8) (NORMAL SUB7) (NORMAL SUB3)
               (PRESENT G1) (PRESENT G8) (PRESENT SUB10) (PRESENT SUB6)
               (PRESENT G36) (PRESENT G56) (PRESENT G55) (PRESENT G54)
               (PRESENT SUB12) (PRESENT G28) (PRESENT SUB15)
               (PRESENT G9) (PRESENT G49) (PRESENT SUB5)
               (PRESENT SUB11) (PRESENT SUB2) (PRESENT G10)
               (PRESENT SUB9) (PRESENT SUB13) (PRESENT SUB14)
               (PRESENT G60) (PRESENT SUB1) (PRESENT SUB4)
               (PRESENT SUB8) (PRESENT SUB7) (PRESENT SUB3)
               (CW SUB3 G1) (CW SUB7 SUB3) (CW SUB8 SUB7)
               (CW SUB4 SUB8) (CW SUB1 SUB4) (CW G60 SUB1)
               (CW SUB14 G60) (CW SUB13 SUB14) (CW SUB9 SUB13)
               (CW G10 SUB9) (CW SUB2 G10) (CW SUB11 SUB2)
               (CW SUB5 SUB11) (CW G49 SUB5) (CW G9 G49) (CW SUB15 G9)
               (CW G28 SUB15) (CW SUB12 G28) (CW G54 SUB12)
               (CW G55 G54) (CW G56 G55) (CW G36 G56) (CW SUB6 G36)
               (CW SUB10 SUB6) (CW G8 SUB10) (CW G1 G8) (IDLE)
               (= (TOTAL-COST) 0))
        (:GOAL (AND (NORMAL G1) (NORMAL SUB10) (NORMAL SUB14)
                    (NORMAL G8) (NORMAL G9) (NORMAL G10) (NORMAL G49)
                    (INVERTED SUB12) (NORMAL G28) (NORMAL SUB6)
                    (INVERTED SUB11) (INVERTED G60) (INVERTED SUB13)
                    (INVERTED G56) (NORMAL SUB9) (INVERTED SUB1)
                    (NORMAL SUB15) (INVERTED SUB5) (INVERTED G36)
                    (NORMAL G54) (INVERTED SUB2) (INVERTED SUB8)
                    (NORMAL SUB4) (NORMAL SUB7) (INVERTED G55)
                    (NORMAL SUB3) (CW SUB3 G1) (CW G55 SUB3)
                    (CW SUB7 G55) (CW SUB4 SUB7) (CW SUB8 SUB4)
                    (CW SUB2 SUB8) (CW G54 SUB2) (CW G36 G54)
                    (CW SUB5 G36) (CW SUB15 SUB5) (CW SUB1 SUB15)
                    (CW SUB9 SUB1) (CW G56 SUB9) (CW SUB13 G56)
                    (CW G60 SUB13) (CW SUB11 G60) (CW SUB6 SUB11)
                    (CW G28 SUB6) (CW SUB12 G28) (CW G49 SUB12)
                    (CW G10 G49) (CW G9 G10) (CW G8 G9) (CW SUB14 G8)
                    (CW SUB10 SUB14) (CW G1 SUB10)))
        (:METRIC MINIMIZE (TOTAL-COST)))