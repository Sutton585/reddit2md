# reddit2md refactor for more robust queries
## Summary
Way more advanced scraping logic is now possible that I was awere of when i first built this module. We need to slightly adjust our logic to take advantage. The core of how it works will be unchanged, but there is an initial process that translates parts of the user's query into a URL that needs to be expanded-upon.

## What's needed
New file to serve as the translator from user's query to a URL. Needs a comprehensive list of what's possible to specify in our initial query to reddit, then have a clear process to translate any combination of the paraemters the user may pass into a working URL with .rss integreated in the URL itself.

### Next steps:
1. Full list of parameters that can be used for a query and integrated into the URL. one new one that we didn't support is "query". We can now support a literal search.
	- For each one, how can we explain the logic of how to include it?
	- How does this affect how we currently approach things in our current codebase?
		For example, if user config file has something in their routine with a name of "reddit serach", and they specify multiple sources (subreddits) (like "marvelComics", "marvelStudios") that gets translated into multiple calls 	(one call to reddit.com/r/marvel Studios, one call to reddit.com/marvelComics). But we now know we can make one call, one URL with mutiple sources/subreddits.
2. Full list of the parameters that we support that must take place outside of the URL. for example `rescrape_threshold_hours` and `debug` are about our tool's functionality, not the query itself.
3. Full plan for this task: 
	1. create new python file to contain all the logic of translating what we can from user query into URL.
	2. ensure it works.
	3. refactor to use the new code, remove old.
	4. re-assess the file README.md in reddit2md. We must NEVER completely rewrite a file. We need a list of surgical additions or corrections to make the readme accurate.
	5. get user approval to make those changes.

## Core Logic of reddit2md
Previously the logic of reddit2md was something like this:
1. User says the scrape “source” is MarvelComics. So that’s our base URL: reddit.com/r/MarvelComics
2. User can specify a sort method (new, top, best, controversial, etc.) to get our results in a particular order.
3. Translate that URL to rss feed, and gather a list of the post names and URLs from that RSS list
4. Using that list, we can do more logic like discarding anything above a certain age, look for certain flair, discard other flair, look for certain text, discard posts with other text. Blah blah blah.

Here’s what I’m now realizing it possible....

1. User says the scrape “source” is MarvelComics. So that’s our base URL: reddit.com/r/MarvelComics
2. User can specify a sort (new, top, best, controversial, etc.) to get our results in a particular order.
3. Translate to rss feed, and gather a list of the post names and URLs from that RSS list. 
ALSO
They can ALSO specify so many other complex things in that URL before we ever turn it into an RSS feed. We can do a complex query in the URL, then translate the URL to a rss feed that is essentially the results of that query. We can get very detailed in our queries this way, then turn that URL to rss and show the results to the users.

## Constraint to always be aware of
The work-around method we use to scrape reddit is by exploiting the fact that we can create one-off rss feeds from URLs. It appears that reddit will always cap those at 25 posts at a time. We will probably never get access to more than 25 posts in a querie, so to the filtering we can do BEFORE it turns into an rss feed, the better.

**Example of more useful and complex logic in URL:**
	I can look for content with a particular flair:
	reddit.com/r/LeaksAndRumors/?f=flair_name%3A%22Comics%22

That translates roughly to:
	reddit.com/r/LeaksAndRumors/?f=flair_name:”Comics”

So I’m not just looking for that flair in my query results. I’m making a query of items with that flair included in the query itself. Way more powerful. I just need to adjust the logic of reddit2md a bit. Instead of adding “.rss” blindly to the end of my any url, I would instead need something like this: `reddit.com/r/LeaksAndRumors/.rss?f=flair_name%3A%22Comics%22`

I can do it with actual search queries too, like this: `/r/LeaksAndRumors/search.rss?q=`

If I have the desire, I could even make a far more complex query, get the results as rss, then filter through the results, instead of just getting a large query and filtering down in those results. I could use logic like this:

 in the subreddit called LeaksAndRumors, I want to look for:
 	flair_text:("Comic" OR "Movie") AND search query of: (marvel OR mcc OR doomsday OR avengers OR "spider-man" OR "spider man" OR "x-men")

That’s so much more fine-tuned, allowing me up to 25 way more useful results. And it's all totally doable. I’d use these sort of tactics:

- flair_text:("Comic" OR "Movie") — partial, case-insensitive flair match; catches "Comics", "Comic Books", "Movies", "Movie Rumor", etc.
- The second (...) block — keyword search within those posts
- AND — both conditions must be true
- restrict_sr=on — keeps results inside this one subreddit
- sort=new — newest first
- t=all — don't limit by time window

**URL encoded piece by piece:**

| Human | Encoded |
|-------|---------|
| `flair_text:` | `flair_text%3A` |
| `("Comic" OR "Movie")` | `%28%22Comic%22+OR+%22Movie%22%29` |
| `AND` | `AND` |
| `(marvel OR ...)` | `%28marvel+OR+mcc+OR+doomsday+OR+avengers+OR+%22spider-man%22+OR+%22spider+man%22+OR+%22x-men%22%29` |

**Final RSS URL:**
```
https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair_text%3A%28%22Comic%22+OR+%22Movie%22%29+AND+%28marvel+OR+mcc+OR+doomsday+OR+avengers+OR+%22spider-man%22+OR+%22spider+man%22+OR+%22x-men%22%29&restrict_sr=on&sort=new&t=all
```

## Variations Worth Knowing

**Flair only, no keywords** (everything in Comics or Movies, newest):
```
https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair_text%3A%28%22Comic%22+OR+%22Movie%22%29&restrict_sr=on&sort=new&t=all
```

**AND flair logic** (post must have BOTH — rare but possible if a post has multiple flairs):
```
flair_text:"Comic" AND flair_text:"Movie"
→ flair_text%3A%22Comic%22+AND+flair_text%3A%22Movie%22
```

**Keyword only, no flair filter:**
```
https://www.reddit.com/r/LeaksAndRumors/search.rss?q=marvel+OR+doomsday+OR+avengers&restrict_sr=on&sort=new&t=all
```

## More Complete List of Reddit Search URL Parameters

### Base URL Structure
```
https://www.reddit.com/r/{subreddit}/search.rss?q={query}&{params}
```
You can also search **all of Reddit** by dropping the subreddit:
```
https://www.reddit.com/search.rss?q={query}&{params}
```

### The `q=` Query Field — The Powerhouse

This is where most of your filtering lives. It supports Lucene-style search syntax.

**Special field operators:**

| Operator | Example | What it does |
|---|---|---|
| `flair_text:` | `flair_text:"Comics"` | Partial/case-insensitive flair match |
| `flair_name:` | `flair_name:"Comics"` | Exact flair match |
| `title:` | `title:avengers` | Search only post titles |
| `selftext:` | `selftext:spoiler` | Search only post body text |
| `author:` | `author:username` | Posts by a specific user |
| `subreddit:` | `subreddit:movies` | Useful when searching all of Reddit |
| `url:` | `url:youtube.com` | Filter by linked domain |
| `site:` | `site:youtube.com` | Similar to url: |
| `nsfw:` | `nsfw:yes` / `nsfw:no` | Filter adult content |
| `self:` | `self:yes` / `self:no` | Text posts only / link posts only |
| `score:` | `score:>100` | Filter by upvote score (unreliable in practice) |

**Logic operators:**

| Operator | Example |
|---|---|
| `AND` | `flair_text:"Comics" AND avengers` |
| `OR` | `marvel OR avengers` |
| `NOT` | `marvel NOT disney` |
| `" "` (quotes) | `"spider man"` — exact phrase |
| `( )` | `(marvel OR dc) AND flair_text:"Comics"` |

### The Other URL Parameters

**`restrict_sr=`**
- `on` — restricts results to the specified subreddit
- Omit or `off` — searches all of Reddit (only useful if you dropped the `/r/subreddit/` part anyway)

**`sort=`**
| Value | Behavior |
|---|---|
| `new` | Newest posts first — best for RSS feeds |
| `relevance` | Default; ranked by match quality |
| `top` | Highest upvoted |
| `hot` | Reddit's "hot" algorithm |
| `comments` | Most commented |

**`t=`** (time filter — only meaningful with `sort=top` or `sort=relevance`)
| Value | Window |
|---|---|
| `hour` | Past hour |
| `day` | Past 24 hours |
| `week` | Past week |
| `month` | Past month |
| `year` | Past year |
| `all` | All time |

**`type=`**
| Value | What it returns |
|---|---|
| `link` | Link posts only |
| `self` | Text posts only |
| *(omit)* | Both |

**`include_over_18=`**
- `on` — include NSFW results
- `off` — exclude them (default)

**`count=` and `after=`**
- Used for pagination. `after=` takes a post's "fullname" (like `t3_abc123`). Less useful for RSS but good to know.

### Multi-Subreddit RSS (no search required)

Reddit natively supports combining subreddits in a feed without any search query:
```
https://www.reddit.com/r/movies+marvelstudios+DC_Cinematic/.rss
```
Just join subreddit names with `+`. You can combine this with search too:
```
https://www.reddit.com/r/movies+marvelstudios/search.rss?q=avengers&restrict_sr=on&sort=new
```

### A Practical Complex Example

*All posts across movies + marvelstudios, with Comics or Movies flair, mentioning specific terms, sorted by new, text or link posts, all time:*
```
https://www.reddit.com/r/movies+marvelstudios/search.rss?q=flair_text%3A%28%22Comic%22+OR+%22Movie%22%29+AND+%28avengers+OR+%22x-men%22%29+NOT+disney&restrict_sr=on&sort=new&t=all&include_over_18=off
```

### Limitations Worth Knowing

- Reddit's search index **lags by minutes to hours** — `sort=new` in RSS may miss very fresh posts temporarily
- `score:` filtering is **unreliable** and often ignored by Reddit's search engine
- `flair_text:` is partial match; `flair_name:` tends to be exact — when in doubt, use `flair_text:`
- Reddit caps RSS feeds at **25 items** — there's no way to increase this natively
- Some subreddits with heavy mod customization may have search behave oddly with flair











