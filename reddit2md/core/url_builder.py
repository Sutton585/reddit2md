"""
reddit2md/core/url_builder.py

Translates a reddit2md task configuration into a precise Reddit RSS URL.
"""

from urllib.parse import urlencode

class URLBuilder:
    """
    Builds Reddit RSS feed URLs from reddit2md task configuration parameters.

    Two URL modes:
    - Simple Browse: Used when no query/flair/filter params are present.
      Format: reddit.com/r/{source}/{sort}/.rss

    - Search: Used when any filtering occurs.
      Format: reddit.com/r/{source}/search.rss?q=...&sort=...&...
    """

    BASE = "https://www.reddit.com"

    def build_rss_url(
        self,
        source=None,
        sort="new",
        timeframe=None,
        post_type=None,
        allow_nsfw=False,
        label=None,
        label_exact=None,
        exclude_label=None,
        exclude_terms=None,
        exclude_urls=None,
        exclude_author=None,
        author=None,
        domain=None,
        selftext=None,
        title_search=None,
        nsfw_only=False,
        spoiler=False,
        search=None,
        **kwargs  # absorbs all other config keys safely
    ):
        """
        Build a Reddit RSS URL from task configuration parameters.
        """
        source_str = self._normalize_source(source)

        is_search_sort = sort in ("relevance", "comments")
        has_q_params = any([label, exclude_label, exclude_terms, exclude_urls, exclude_author, author, domain, selftext, title_search, nsfw_only, spoiler, search])
        has_exact_flair_search = label_exact and sort != "new"

        needs_search = any([
            is_search_sort,
            has_q_params,
            has_exact_flair_search,
            timeframe,
            post_type,
            allow_nsfw is True
        ])

        if not needs_search and label_exact and sort == "new":
            # BROWSE endpoint with f=flair_name:
            return self._build_browse_url_with_flair(source_str, sort, label_exact)

        if not needs_search:
            return self._build_browse_url(source_str, sort)

        return self._build_search_url(
            source_str=source_str,
            sort=sort,
            timeframe=timeframe,
            post_type=post_type,
            allow_nsfw=allow_nsfw,
            label=label,
            label_exact=label_exact if has_exact_flair_search else None,
            exclude_label=exclude_label,
            exclude_terms=exclude_terms,
            exclude_urls=exclude_urls,
            exclude_author=exclude_author,
            author=author,
            domain=domain,
            selftext=selftext,
            title_search=title_search,
            nsfw_only=nsfw_only,
            spoiler=spoiler,
            search=search
        )

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _normalize_source(self, source):
        if not source or str(source).lower() in ("all", "none", ""):
            return None
        if isinstance(source, list):
            parts = [s.strip() for s in source if s.strip()]
            return "+".join(parts) if parts else None
        return str(source).strip() or None

    def _build_browse_url(self, source_str, sort):
        if source_str:
            return f"{self.BASE}/r/{source_str}/{sort}/.rss"
        else:
            return f"{self.BASE}/{sort}/.rss"

    def _build_browse_url_with_flair(self, source_str, sort, label_exact):
        base = self._build_browse_url(source_str, sort)
        return f"{base}?f=flair_name%3A%22{label_exact}%22"

    def _build_q_string(
        self, label, label_exact, exclude_label, exclude_terms, exclude_urls, exclude_author, author, domain, selftext, title_search, nsfw_only, spoiler, search
    ):
        q_parts = []

        if label:
            if isinstance(label, list):
                terms = " OR ".join(f'"{l}"' for l in label)
                q_parts.append(f"flair:({terms})")
            else:
                q_parts.append(f'flair:"{label}"')

        if label_exact:
            q_parts.append(f'flair_name:"{label_exact}"')

        if exclude_label:
            for el in (exclude_label if isinstance(exclude_label, list) else [exclude_label]):
                q_parts.append(f'NOT flair:"{el}"')

        if exclude_terms:
            for et in (exclude_terms if isinstance(exclude_terms, list) else [exclude_terms]):
                q_parts.append(f'NOT "{et}"')

        if exclude_urls:
            for eu in (exclude_urls if isinstance(exclude_urls, list) else [exclude_urls]):
                q_parts.append(f"NOT site:{eu}")

        if exclude_author:
            for ea in (exclude_author if isinstance(exclude_author, list) else [exclude_author]):
                q_parts.append(f"NOT author:{ea}")

        if author:
            for auth in (author if isinstance(author, list) else [author]):
                q_parts.append(f"author:{auth}")

        if domain:
            for dom in (domain if isinstance(domain, list) else [domain]):
                q_parts.append(f"site:{dom}")

        if title_search:
            for ts in (title_search if isinstance(title_search, list) else [title_search]):
                q_parts.append(f"title:{ts}")

        if selftext:
            for st in (selftext if isinstance(selftext, list) else [selftext]):
                q_parts.append(f"selftext:{st}")
                
        if nsfw_only:
            q_parts.append("nsfw:yes")
            
        if spoiler:
            q_parts.append("spoiler:yes")

        if search:
            if q_parts:
                return " AND ".join(q_parts) + f" AND {search}"
            else:
                return search
        else:
            return " AND ".join(q_parts)

    def _build_search_url(
        self, source_str, sort, timeframe, post_type, allow_nsfw,
        label, label_exact, exclude_label, exclude_terms, exclude_urls, exclude_author, author, domain, selftext, title_search, nsfw_only, spoiler, search
    ):
        q_string = self._build_q_string(
            label, label_exact, exclude_label, exclude_terms, exclude_urls, exclude_author, author, domain, selftext, title_search, nsfw_only, spoiler, search
        )

        params = {}
        if q_string:
            params["q"] = q_string
        if source_str:
            params["restrict_sr"] = "on"
        if sort:
            params["sort"] = sort
        if timeframe:
            params["t"] = timeframe
        if post_type:
            params["type"] = post_type
            
        params["include_over_18"] = "on" if allow_nsfw else "off"

        if source_str:
            base = f"{self.BASE}/r/{source_str}/search.rss"
        else:
            base = f"{self.BASE}/search.rss"

        return f"{base}?{urlencode(params)}"


# =============================================================================
# Standalone verification block
# Run: python -m reddit2md.core.url_builder
# =============================================================================

if __name__ == "__main__":
    builder = URLBuilder()
    passed = 0
    failed = 0

    def check(label_desc, result, expected):
        global passed, failed
        if result == expected:
            print(f"  ✅ PASS: {label_desc}")
            passed += 1
        else:
            print(f"  ❌ FAIL: {label_desc}")
            print(f"     Got:      {result}")
            print(f"     Expected: {expected}")
            failed += 1

    print("\n--- Simple Browse (no search params) ---")
    check(
        "Basic subreddit + sort",
        builder.build_rss_url(source="Python", sort="new"),
        "https://www.reddit.com/r/Python/new/.rss"
    )
    check(
        "Global hot feed",
        builder.build_rss_url(source=None, sort="hot"),
        "https://www.reddit.com/hot/.rss"
    )
    check(
        "source='all' treated as global",
        builder.build_rss_url(source="all", sort="new"),
        "https://www.reddit.com/new/.rss"
    )

    print("\n--- Flair Filtering ---")
    check(
        "Single label (partial flair match)",
        builder.build_rss_url(source="LeaksAndRumors", label="Comics", allow_nsfw=False),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair%3A%22Comics%22&restrict_sr=on&sort=new&include_over_18=off"
    )
    check(
        "label_exact with sort=new (Browse Safe)",
        builder.build_rss_url(source="LeaksAndRumors", label_exact="Comics", sort="new"),
        "https://www.reddit.com/r/LeaksAndRumors/new/.rss?f=flair_name%3A%22Comics%22"
    )
    check(
        "label_exact with sort=top (Search Mode)",
        builder.build_rss_url(source="LeaksAndRumors", label_exact="Comics", sort="top"),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair_name%3A%22Comics%22&restrict_sr=on&sort=top&include_over_18=off"
    )
    check(
        "Multi-value label (OR list)",
        builder.build_rss_url(source="LeaksAndRumors", label=["Comic", "Movie"], sort="new"),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair%3A%28%22Comic%22+OR+%22Movie%22%29&restrict_sr=on&sort=new&include_over_18=off"
    )

    print("\n--- Exclude Filters ---")
    check(
        "exclude_terms as list",
        builder.build_rss_url(source="LeaksAndRumors", exclude_terms=["Marvel", "DC"], sort="new"),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=NOT+%22Marvel%22+AND+NOT+%22DC%22&restrict_sr=on&sort=new&include_over_18=off"
    )
    check(
        "exclude_label as list",
        builder.build_rss_url(source="Leaks", exclude_label=["Spoilers", "Rumor"], sort="new"),
        "https://www.reddit.com/r/Leaks/search.rss?q=NOT+flair%3A%22Spoilers%22+AND+NOT+flair%3A%22Rumor%22&restrict_sr=on&sort=new&include_over_18=off"
    )
    check(
        "exclude_author as list",
        builder.build_rss_url(source="Leaks", exclude_author=["AutoModerator", "Bot"], sort="new"),
        "https://www.reddit.com/r/Leaks/search.rss?q=NOT+author%3AAutoModerator+AND+NOT+author%3ABot&restrict_sr=on&sort=new&include_over_18=off"
    )
    check(
        "exclude_urls as list",
        builder.build_rss_url(source="Leaks", exclude_urls=["imgur.com", "youtube.com"], sort="new"),
        "https://www.reddit.com/r/Leaks/search.rss?q=NOT+site%3Aimgur.com+AND+NOT+site%3Ayoutube.com&restrict_sr=on&sort=new&include_over_18=off"
    )

    print("\n--- Keyword Queries ---")
    check(
        "Simple keyword query",
        builder.build_rss_url(source="LeaksAndRumors", search="avengers", sort="new"),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=avengers&restrict_sr=on&sort=new&include_over_18=off"
    )
    check(
        "Search + label combined",
        builder.build_rss_url(
            source="LeaksAndRumors",
            label="Comic",
            search="marvel OR avengers",
            sort="new"
        ),
        "https://www.reddit.com/r/LeaksAndRumors/search.rss?q=flair%3A%22Comic%22+AND+marvel+OR+avengers&restrict_sr=on&sort=new&include_over_18=off"
    )

    print("\n--- Multi-Source ---")
    check(
        "Plus-joined string source",
        builder.build_rss_url(source="movies+marvelstudios", post_type="link"),
        "https://www.reddit.com/r/movies+marvelstudios/search.rss?restrict_sr=on&sort=new&type=link&include_over_18=off"
    )
    check(
        "List source",
        builder.build_rss_url(source=["movies", "marvelstudios"], post_type="link"),
        "https://www.reddit.com/r/movies+marvelstudios/search.rss?restrict_sr=on&sort=new&type=link&include_over_18=off"
    )

    print("\n--- Time Filter + NSFW ---")
    check(
        "Top of week",
        builder.build_rss_url(source="Python", sort="top", timeframe="week"),
        "https://www.reddit.com/r/Python/search.rss?restrict_sr=on&sort=top&t=week&include_over_18=off"
    )
    check(
        "NSFW enabled",
        builder.build_rss_url(source="all", search="art", allow_nsfw=True),
        "https://www.reddit.com/search.rss?q=art&sort=new&include_over_18=on"
    )
    check(
        "post_type only",
        builder.build_rss_url(source="Python", sort="new", post_type="link"),
        "https://www.reddit.com/r/Python/search.rss?restrict_sr=on&sort=new&type=link&include_over_18=off"
    )
    check(
        "allow_nsfw only",
        builder.build_rss_url(source="Python", sort="new", allow_nsfw=True),
        "https://www.reddit.com/r/Python/search.rss?restrict_sr=on&sort=new&include_over_18=on"
    )
    check(
        "sort=relevance no other params",
        builder.build_rss_url(source="Python", sort="relevance"),
        "https://www.reddit.com/r/Python/search.rss?restrict_sr=on&sort=relevance&include_over_18=off"
    )

    print("\n--- Config Dict Pass-through (extra keys ignored) ---")
    full_config = {
        "source": "Python",
        "sort": "new",
        "label": "Help",
        "rescrape_newer_than_hours": 24,       # should be silently absorbed
        "ignore_below_score": 50,              # should be silently absorbed
        "ignore_newer_than_hours": 10,         # should be silently absorbed
    }
    check(
        "Full config dict passed via **",
        builder.build_rss_url(**full_config),
        "https://www.reddit.com/r/Python/search.rss?q=flair%3A%22Help%22&restrict_sr=on&sort=new&include_over_18=off"
    )

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("All tests passed ✅")
    else:
        print("Some tests FAILED ❌ — review output above")
