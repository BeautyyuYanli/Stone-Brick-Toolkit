from tenacity import stop_after_attempt, stop_never


def stop_after_attempt_with_inf(max_attempts: int):
    return stop_after_attempt(max_attempts) if max_attempts >= 0 else stop_never
