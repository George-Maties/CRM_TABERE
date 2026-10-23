import logging
import time

from django.db import connection

logger = logging.getLogger("apps.queries")

# More queries than this on one page usually means one per row (N+1): logged as a warning.
MANY_QUERIES = 30


class QueryStatsMiddleware:
    """DEBUG only (see settings): logs, for every page, how many SQL queries it ran and how
    long they and the whole request took, e.g. "GET /contacte/ 200 · 9 queries, 14 ms SQL,
    61 ms total". Shows which pages get slower as the data grows."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        stats = {"count": 0, "sql": 0.0}

        def measure(execute, sql, params, many, context):
            started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                stats["count"] += 1
                stats["sql"] += time.perf_counter() - started

        started = time.perf_counter()
        with connection.execute_wrapper(measure):
            response = self.get_response(request)
        total = time.perf_counter() - started
        log = logger.warning if stats["count"] > MANY_QUERIES else logger.info
        log(
            "%s %s %s · %d queries, %.0f ms SQL, %.0f ms total",
            request.method,
            request.get_full_path(),
            response.status_code,
            stats["count"],
            stats["sql"] * 1000,
            total * 1000,
        )
        return response
