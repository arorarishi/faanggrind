# Longest Substring Without Repeating Characters · FAANGrind

Source: https://faangrind.vercel.app/problems/longest-substring-without-repeating-characters

[All problems](/problems)

#923Medium· asked at 51 companies

# Longest Substring Without Repeating Characters

[![](/logos/deloitte.ico)Deloitte](/companies/deloitte)[![](/logos/cisco.ico)Cisco](/companies/cisco)[![](/logos/paypal.png)PayPal](/companies/paypal)[![](/logos/cognizant.png)Cognizant](/companies/cognizant)[![](/logos/zoho.ico)Zoho](/companies/zoho)[![](/logos/agoda.png)Agoda](/companies/agoda)+45 more

Hosted on LeetCode

## Solve it on LeetCode, track it here.

This problem's full statement lives on LeetCode. Open it in a new tab, then come back to mark it solved, add notes and keep your streak.

[Open on LeetCode](https://leetcode.com/problems/longest-substring-without-repeating-characters/) [Watch a solution](https://www.youtube.com/results?search_query=Longest%20Substring%20Without%20Repeating%20Characters%20dsa)

### LeetCode Premium locked?

Most company-tagged LeetCode problems are behind Premium. If you have ChatGPT Plus or Claude Pro, ask it for the full statement, examples and constraints. The buttons below open a chat with the prompt already filled in.

[Ask ChatGPT](https://chatgpt.com/?q=Give%20me%20the%20full%20problem%20statement%20for%20the%20LeetCode%20problem%20%22Longest%20Substring%20Without%20Repeating%20Characters%22%20(it%20is%20a%20premium%2Flocked%20problem)%3A%20the%20description%2C%20input%2Foutput%20format%2C%202%E2%80%933%20worked%20examples%20with%20explanations%2C%20and%20constraints.%20Do%20not%20give%20the%20solution%20yet.) [Ask Claude](https://claude.ai/new?q=Give%20me%20the%20full%20problem%20statement%20for%20the%20LeetCode%20problem%20%22Longest%20Substring%20Without%20Repeating%20Characters%22%20(it%20is%20a%20premium%2Flocked%20problem)%3A%20the%20description%2C%20input%2Foutput%20format%2C%202%E2%80%933%20worked%20examples%20with%20explanations%2C%20and%20constraints.%20Do%20not%20give%20the%20solution%20yet.)

## What we know

Example 1

```
Input: s = "abcabcbb"
Output: 3
```

The answer is "abc".

Example 2

```
Input: s = "bbbbb"
Output: 1
```

Example 3

```
Input: s = "pwwkew"
Output: 3
```

The answer is "wke".

## Constraints

* •

  `0 <= s.length <= 5 * 10^4`
* •

  `s` consists of English letters, digits, symbols and spaces.

## Hintsreveal one at a time

[PreviousLRU Cache](/problems/lru-cache)[NextMerge Intervals](/problems/merge-intervals)

Saved in this browser. No account needed.

## Asked at

51 companies

* [![](/logos/deloitte.ico)Deloitte#1 in list](/companies/deloitte)
* [![](/logos/cisco.ico)Cisco#2 in list](/companies/cisco)
* [![](/logos/paypal.png)PayPal#4 in list](/companies/paypal)
* [![](/logos/cognizant.png)Cognizant#9 in list](/companies/cognizant)
* [![](/logos/zoho.ico)Zoho#9 in list](/companies/zoho)
* [![](/logos/agoda.png)Agoda#11 in list](/companies/agoda)
* [![](/logos/netflix.png)Netflix#11 in list](/companies/netflix)
* [![](/logos/capgemini.png)Capgemini#13 in list](/companies/capgemini)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#13 in list](/companies/palo-alto-networks)
* [![](/logos/flipkart.png)Flipkart#14 in list](/companies/flipkart)
* [![](/logos/qualcomm.png)Qualcomm#14 in list](/companies/qualcomm)
* [![](/logos/roblox.png)Roblox#17 in list](/companies/roblox)
* [![](/logos/paytm.png)Paytm#23 in list](/companies/paytm)
* [![](/logos/goldman-sachs.png)Goldman Sachs#24 in list](/companies/goldman-sachs)
* [![](/logos/zomato.png)Zomato#24 in list](/companies/zomato)
* [![](/logos/epam-systems.jpg)EPAM Systems#27 in list](/companies/epam-systems)
* [![](/logos/coupang.ico)Coupang#28 in list](/companies/coupang)
* [![](/logos/sap.png)SAP#28 in list](/companies/sap)
* [![](/logos/tesla.ico)Tesla#35 in list](/companies/tesla)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#36 in list](/companies/walmart-global-tech)
* [![](/logos/swiggy.png)Swiggy#37 in list](/companies/swiggy)
* [![](/logos/apple.ico)Apple#43 in list](/companies/apple)
* [![](/logos/servicenow.png)ServiceNow#46 in list](/companies/servicenow)
* [![](/logos/adobe.ico)Adobe#50 in list](/companies/adobe)
* [![](/logos/ebay.ico)eBay#55 in list](/companies/ebay)
* [![](/logos/snap.png)Snap#58 in list](/companies/snap)
* [![](/logos/morgan-stanley.png)Morgan Stanley#60 in list](/companies/morgan-stanley)
* [![](/logos/linkedin.ico)LinkedIn#61 in list](/companies/linkedin)
* [![](/logos/capital-one.png)Capital One#62 in list](/companies/capital-one)
* [![](/logos/nutanix.png)Nutanix#63 in list](/companies/nutanix)
* [![](/logos/expedia.ico)Expedia Group#64 in list](/companies/expedia)
* [![](/logos/meta.ico)Meta#64 in list](/companies/meta)
* [![](/logos/tcs.png)TCS#67 in list](/companies/tcs)
* [![](/logos/uber.ico)Uber#68 in list](/companies/uber)
* [![](/logos/yandex.png)Yandex#72 in list](/companies/yandex)
* [![](/logos/atlassian.ico)Atlassian#77 in list](/companies/atlassian)
* [![](/logos/visa.ico)Visa#90 in list](/companies/visa)
* [![](/logos/accenture.ico)Accenture#108 in list](/companies/accenture)
* [![](/logos/tiktok.png)TikTok#113 in list](/companies/tiktok)
* [![](/logos/salesforce.ico)Salesforce#115 in list](/companies/salesforce)
* [![](/logos/amazon.ico)Amazon#117 in list](/companies/amazon)
* [![](/logos/de-shaw.ico)D. E. Shaw#123 in list](/companies/de-shaw)
* [![](/logos/infosys.png)Infosys#123 in list](/companies/infosys)
* [![](/logos/bloomberg.ico)Bloomberg#140 in list](/companies/bloomberg)
* [![](/logos/ibm.ico)IBM#141 in list](/companies/ibm)
* [![](/logos/nvidia.ico)NVIDIA#141 in list](/companies/nvidia)
* [![](/logos/american-express.png)American Express#153 in list](/companies/american-express)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#157 in list](/companies/jpmorgan-chase)
* [![](/logos/microsoft.ico)Microsoft#163 in list](/companies/microsoft)
* [![](/logos/oracle.ico)Oracle#234 in list](/companies/oracle)
* [![](/logos/google.ico)Google#249 in list](/companies/google)

## Details

Difficulty
:   Medium

Popularity
:   90/100

Source
:   LeetCode

Topics
:   [Strings](/topics?open=strings#strings)

[LeetCode](https://leetcode.com/problems/longest-substring-without-repeating-characters/) [Solution](https://www.youtube.com/results?search_query=Longest%20Substring%20Without%20Repeating%20Characters%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#909Longest Palindromic SubstringMedium](/problems/longest-palindromic-substring)
* [#1313Minimum Window SubstringMedium](/problems/minimum-window-substring)
* [#1951Valid AnagramEasy](/problems/valid-anagram)
* [#1463Palindrome CheckMedium](/problems/palindrome-check)
* [#911Longest Repeating Character ReplacementMedium](/problems/longest-repeating-character-replacement)
* [#1810String CompressionMedium](/problems/string-compression)
