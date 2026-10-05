# search aliases

Used by the search engine (automatic recall and recall.sh) to expand queries. When a whole query equals one member of a line, the other members are searched too. Sessions never read this file.
One group per line, `- word1 = word2 = word3`, all meaning the same thing. Add a line when an old name was replaced or a thing has several names. Leave out very common short words and generic English words, or query expansion will explode.

- notebook = cortex = memory store
- curator = hippocampus
- nb-grep = recall.sh = recall
