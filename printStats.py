import pstats

profStats = pstats.Stats('./stats')
profStats.sort_stats('cumulative')
profStats.print_stats()
