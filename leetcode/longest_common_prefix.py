# https://leetcode.com/problems/longest-common-prefix/

class Solution:
        
    def longestCommonPrefix(self, strs) -> str:
#         this will be the prefix string and will be set to the first character of the first word by default
        
        strs = strs.split(' ')
        is_True = False
        length = 0
        # Find the shortest word
        for word in strs:
            if length == 0:
                length = len(word)
                shortest_word = word
            elif len(word) < length:
                shortest_word = word
        # 
        for i in range(len(shortest_word)): 
            prefix_string = shortest_word[i]
            for j in range(len(strs)):
                if strs[j][i] == prefix_string:
                    continue
                else:
                    if i ==0:
                        return ""
                    else:
                        return word[:i]
        return word[:i+1]

if __name__ == '__main__':
    low = input("Enter a list element separated by space")
    s = Solution()
    print(s.longestCommonPrefix(low))