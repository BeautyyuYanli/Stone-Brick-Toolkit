from tenacity import stop_after_attempt, stop_never


def stop_after_attempt_may_inf(max_attempts: int):
    """
    max_attempts >= 0 means stop after max_attempts attempts, otherwise, never stop.
    """
    return stop_after_attempt(max_attempts) if max_attempts >= 0 else stop_never
