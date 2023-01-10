# https://leetcode.com/problems/roman-to-integer/

import argparse

mapping_dict = {
    "0": 0,
    "I": 1,
    "IV": 4,
    "V": 5,
    "IX": 9,
    "X": 10,
    "XL": 40,
    "L": 50,
    "XC": 90,
    "C": 100,
    "CD": 400,
    "D": 500,
    "CM": 900,
    "M": 1000
}

# How would you write 3999
# MMMCMXLIX
class Solution:
    @staticmethod
    def romanToInt(s: str) -> int:
        """
        This function takes a roman numeral 
        of less than 15 characters and returns and int
        """
#         Calc Answer
        answer = 0
        previous_value = None
        skip = False
        for i in range(len(s)):
# Look at the previous value, if the previous value is lower than the next value then combine the 2 else add to answer
            if skip:
                skip=False
                continue
            current_value = s[i]
            try:
                next_value = s[i+1]
#             Error when last value in the string
            except:
                next_value = '0'
            if mapping_dict[current_value] < mapping_dict[next_value]:
                answer += mapping_dict[current_value+next_value]
                skip = True
            else:
                answer += mapping_dict[current_value]
        return answer

if __name__ == '__main__':
    rn = input("Enter a Roman Numeral:")
    print(Solution.romanToInt(rn))
            
        
        
        