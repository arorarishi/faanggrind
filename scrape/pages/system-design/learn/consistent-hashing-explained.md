# Consistent hashing — system design fundamentals · FAANGrind

Source: https://faangrind.vercel.app/system-design/learn/consistent-hashing-explained

[All guides](/system-design/learn)

Building blocksGuide #5 5 min read 10 figures

# Consistent hashing

Why modulo hashing breaks, the hash ring, virtual nodes and which keys move when servers change.

## Introduction

This guide explores consistent hashing, a technique essential for achieving horizontal scaling by efficiently distributing requests and data across servers. It minimizes data redistribution when servers are added or removed and ensures an even distribution of data to mitigate issues like server hotspots.

## The Rehashing Problem

### Explanation

In traditional hashing methods, such as `serverIndex = hash(key) % N`, data redistribution becomes problematic when the number of servers changes. For example:

* Removing a server causes most keys to be reassigned, leading to cache misses.
* Adding a server results in unnecessary key redistributions.

![Server hashing](/fundamentals/consistent-hashing-explained/server-hashing.webp)Server hashing

* This approach works well when the size of the server pool is fixed. However, problems arise when new servers are added, or existing servers are removed.

![Server hashing Miss](/fundamentals/consistent-hashing-explained/server-hashing-miss.webp)Server hashing Miss

### Key Issue

Redistribution of most keys when server count changes causes inefficiency and overload.

## Consistent Hashing

### Definition

Consistent hashing ensures that only a fraction of keys are remapped when servers are added or removed. This minimizes disruptions and enhances scalability.

### Key Concepts

1. **Hash Space and Ring:** The hash space forms a continuous ring, with hash values distributed from `0` to `2^160-1` (e.g., using hash function like SHA-1). By connecting both ends we get a ring.

![Hash Ring](/fundamentals/consistent-hashing-explained/hash-ring.webp)Hash Ring

* Using the same hash function f, we map servers based on server IP or name onto the ring.

![Server Ring](/fundamentals/consistent-hashing-explained/server-ring.webp)Server Ring

1. **Server Lookup**

* A key's server is determined by traversing clockwise on the ring until a server is found.

![Server Lookup](/fundamentals/consistent-hashing-explained/server-lookup.webp)Server Lookup

2. **Adding and Removing Servers**

* Adding a server redistributes only nearby keys. Only a fraction of keys are redistributed to the new server.

![Adding Server](/fundamentals/consistent-hashing-explained/adding-server.webp)Adding Server

* Removing a server affects only the keys in its range. Only keys from the removed server are reassigned to the next server clockwise.

![Removing Server](/fundamentals/consistent-hashing-explained/removing-server.webp)Removing Server

## Challenges and Solutions

### Two Issues in Basic Approach

1. **Uneven Partition Sizes:** Servers may have unequal data partitions.
2. **Non-uniform Key Distribution:** Some servers may receive significantly more keys than others.

### Solution: Virtual Nodes

* Each server is represented by multiple virtual nodes on the ring uniformly distrubuted on the ring.
* Virtual nodes improve key distribution and balance load. As the number of virtual nodes increases, the distribution of keys becomes more balanced. This is because the standard deviation gets smaller with more virtual nodes, leading to balanced data distribution.

![Virtual Nodes](/fundamentals/consistent-hashing-explained/virtual-nodes.webp)Virtual Nodes

## Affected Keys

When servers are added or removed:

* **Added Server:** Affected keys are those between the new server and its predecessor.
  In the following example server 4 is added onto the ring. The affected range starts from s4 (newly
  added node) and moves anticlockwise around the ring until a server is found (s3). Thus, keys
  located between s3 and s4 need to be redistributed to s4.

![Server Addition](/fundamentals/consistent-hashing-explained/server-addition.webp)Server Addition

* **Removed Server:** Affected keys are those between the removed server and its predecessor. In the following example when a server (s1) is removed, the affected range starts from s1
  (removed node) and moves anticlockwise around the ring until a server is found (s0). Thus, keys located between s0 and s1 must be redistributed to s2.

![Server Removed](/fundamentals/consistent-hashing-explained/server-removed.webp)Server Removed

## Benefits of Consistent Hashing

* **Minimized Redistribution:** Only a fraction of keys are reassigned.
* **Scalability:** Enables horizontal scaling.
* **Mitigates Hotspots:** Balances data distribution to avoid server overload.

## Real-World Applications

* Amazon Dynamo DB
* Apache Cassandra
* Discord
* Akamai CDN
* Maglev Load Balancer

[PreviousRate limiting](/system-design/learn/rate-limiting)[NextDistributed key-value stores](/system-design/learn/key-value-stores)

## Practice this

Questions in the bank that use this guide.

* [Consistent Hashing (Data Partitioning)HLDMedium](/system-design/consistent-hashing)
* [Distributed Cache (Redis / Memcached)HLDMedium](/system-design/distributed-cache)
* [Distributed Key-Value Store (Dynamo / Cassandra)HLDHard](/system-design/key-value-store)

## On this page

1. [Introduction](#introduction)
2. [The Rehashing Problem](#the-rehashing-problem)
3. [Consistent Hashing](#consistent-hashing)
4. [Challenges and Solutions](#challenges-and-solutions)
5. [Affected Keys](#affected-keys)
6. [Benefits of Consistent Hashing](#benefits-of-consistent-hashing)
7. [Real-World Applications](#real-world-applications)
