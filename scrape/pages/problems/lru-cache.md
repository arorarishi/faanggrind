# LRU Cache · FAANGrind

Source: https://faangrind.vercel.app/problems/lru-cache

[All problems](/problems)

#934Medium· asked at 52 companies

# LRU Cache

[![](/logos/intuit.png)Intuit](/companies/intuit)[![](/logos/qualcomm.png)Qualcomm](/companies/qualcomm)[![](/logos/de-shaw.ico)D. E. Shaw](/companies/de-shaw)[![](/logos/nutanix.png)Nutanix](/companies/nutanix)[![](/logos/netflix.png)Netflix](/companies/netflix)[![](/logos/walmart-global-tech.ico)Walmart Global Tech](/companies/walmart-global-tech)+46 more

Hosted on LeetCode

## Solve it on LeetCode, track it here.

This problem's full statement lives on LeetCode. Open it in a new tab, then come back to mark it solved, add notes and keep your streak.

[Open on LeetCode](https://leetcode.com/problems/lru-cache/) [Watch a solution](https://www.youtube.com/results?search_query=LRU%20Cache%20dsa)

### LeetCode Premium locked?

Most company-tagged LeetCode problems are behind Premium. If you have ChatGPT Plus or Claude Pro, ask it for the full statement, examples and constraints. The buttons below open a chat with the prompt already filled in.

[Ask ChatGPT](https://chatgpt.com/?q=Give%20me%20the%20full%20problem%20statement%20for%20the%20LeetCode%20problem%20%22LRU%20Cache%22%20(it%20is%20a%20premium%2Flocked%20problem)%3A%20the%20description%2C%20input%2Foutput%20format%2C%202%E2%80%933%20worked%20examples%20with%20explanations%2C%20and%20constraints.%20Do%20not%20give%20the%20solution%20yet.) [Ask Claude](https://claude.ai/new?q=Give%20me%20the%20full%20problem%20statement%20for%20the%20LeetCode%20problem%20%22LRU%20Cache%22%20(it%20is%20a%20premium%2Flocked%20problem)%3A%20the%20description%2C%20input%2Foutput%20format%2C%202%E2%80%933%20worked%20examples%20with%20explanations%2C%20and%20constraints.%20Do%20not%20give%20the%20solution%20yet.)

## What we know

Example 1

```
Input: ["LRUCache","put","put","get","put","get","put","get","get","get"]
[[2],[1,1],[2,2],[1],[3,3],[2],[4,4],[1],[3],[4]]
Output: [null,null,null,1,null,-1,null,-1,3,4]
```

put(3,3) evicts key 2; put(4,4) evicts key 1.

## Constraints

* •

  `1 <= capacity <= 3000`
* •

  `0 <= key <= 10^4`
* •

  `0 <= value <= 10^5`
* •

  At most `2 * 10^5` calls will be made to `get` and `put`.

## Hintsreveal one at a time

[PreviousTwo Sum](/problems/two-sum)[NextLongest Substring Without Repeating Characters](/problems/longest-substring-without-repeating-characters)

Saved in this browser. No account needed.

## Asked at

52 companies

* [![](/logos/intuit.png)Intuit#1 in list](/companies/intuit)
* [![](/logos/qualcomm.png)Qualcomm#2 in list](/companies/qualcomm)
* [![](/logos/de-shaw.ico)D. E. Shaw#5 in list](/companies/de-shaw)
* [![](/logos/nutanix.png)Nutanix#5 in list](/companies/nutanix)
* [![](/logos/netflix.png)Netflix#6 in list](/companies/netflix)
* [![](/logos/walmart-global-tech.ico)Walmart Global Tech#6 in list](/companies/walmart-global-tech)
* [![](/logos/nvidia.ico)NVIDIA#11 in list](/companies/nvidia)
* [![](/logos/sprinklr.png)Sprinklr#11 in list](/companies/sprinklr)
* [![](/logos/snowflake.png)Snowflake#12 in list](/companies/snowflake)
* [![](/logos/visa.ico)Visa#19 in list](/companies/visa)
* [![](/logos/epam-systems.jpg)EPAM Systems#21 in list](/companies/epam-systems)
* [![](/logos/x.png)X (Twitter)#22 in list](/companies/x)
* [![](/logos/capital-one.png)Capital One#27 in list](/companies/capital-one)
* [![](/logos/coupang.ico)Coupang#30 in list](/companies/coupang)
* [![](/logos/expedia.ico)Expedia Group#31 in list](/companies/expedia)
* [![](/logos/doordash.png)DoorDash#32 in list](/companies/doordash)
* [![](/logos/anduril.ico)Anduril#33 in list](/companies/anduril)
* [![](/logos/sap.png)SAP#37 in list](/companies/sap)
* [![](/logos/snap.png)Snap#37 in list](/companies/snap)
* [![](/logos/ebay.ico)eBay#39 in list](/companies/ebay)
* [![](/logos/tesla.ico)Tesla#40 in list](/companies/tesla)
* [![](/logos/samsung.png)Samsung#44 in list](/companies/samsung)
* [![](/logos/bytedance.ico)ByteDance#50 in list](/companies/bytedance)
* [![](/logos/morgan-stanley.png)Morgan Stanley#61 in list](/companies/morgan-stanley)
* [![](/logos/servicenow.png)ServiceNow#63 in list](/companies/servicenow)
* [![](/logos/salesforce.ico)Salesforce#69 in list](/companies/salesforce)
* [![](/logos/flipkart.png)Flipkart#76 in list](/companies/flipkart)
* [![](/logos/citadel.png)Citadel#79 in list](/companies/citadel)
* [![](/logos/palo-alto-networks.png)Palo Alto Networks#84 in list](/companies/palo-alto-networks)
* [![](/logos/cisco.ico)Cisco#85 in list](/companies/cisco)
* [![](/logos/zoho.ico)Zoho#94 in list](/companies/zoho)
* [![](/logos/phonepe.png)PhonePe#95 in list](/companies/phonepe)
* [![](/logos/bloomberg.ico)Bloomberg#99 in list](/companies/bloomberg)
* [![](/logos/adobe.ico)Adobe#102 in list](/companies/adobe)
* [![](/logos/yandex.png)Yandex#112 in list](/companies/yandex)
* [![](/logos/accenture.ico)Accenture#117 in list](/companies/accenture)
* [![](/logos/jpmorgan-chase.png)JPMorgan Chase#118 in list](/companies/jpmorgan-chase)
* [![](/logos/american-express.png)American Express#136 in list](/companies/american-express)
* [![](/logos/linkedin.ico)LinkedIn#153 in list](/companies/linkedin)
* [![](/logos/paypal.png)PayPal#156 in list](/companies/paypal)
* [![](/logos/swiggy.png)Swiggy#156 in list](/companies/swiggy)
* [![](/logos/ibm.ico)IBM#158 in list](/companies/ibm)
* [![](/logos/atlassian.ico)Atlassian#164 in list](/companies/atlassian)
* [![](/logos/microsoft.ico)Microsoft#165 in list](/companies/microsoft)
* [![](/logos/meta.ico)Meta#166 in list](/companies/meta)
* [![](/logos/goldman-sachs.png)Goldman Sachs#206 in list](/companies/goldman-sachs)
* [![](/logos/tiktok.png)TikTok#209 in list](/companies/tiktok)
* [![](/logos/oracle.ico)Oracle#211 in list](/companies/oracle)
* [![](/logos/google.ico)Google#216 in list](/companies/google)
* [![](/logos/uber.ico)Uber#261 in list](/companies/uber)
* [![](/logos/apple.ico)Apple#276 in list](/companies/apple)
* [![](/logos/amazon.ico)Amazon#529 in list](/companies/amazon)

## Details

Difficulty
:   Medium

Popularity
:   91/100

Source
:   LeetCode

Topics
:   [Hashing](/topics?open=hashing#hashing)[Linked List](/topics?open=linked-list#linked-list)

[LeetCode](https://leetcode.com/problems/lru-cache/) [Solution](https://www.youtube.com/results?search_query=LRU%20Cache%20dsa)

## Your notes

Saved

Autosaves to this browser.

## Similar problems

* [#1923Two SumEasy](/problems/two-sum)
* [#1140Merge two Sorted ListsMedium](/problems/merge-two-sorted-lists)
* [#20Add two numbers in Linked ListMedium](/problems/add-two-numbers-in-linked-list)
* [#1897Top K Frequent ElementsMedium](/problems/top-k-frequent-elements)
* [#1134Merge K sorted ListsMedium](/problems/merge-k-sorted-lists)
* [#890Longest Consecutive Sequence in an ArrayMedium](/problems/longest-consecutive-sequence-in-an-array)
