export interface RetryConfig {
  maxAttempts: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

export interface RetryableError {
  retryAfterMs?: number;
}

const jitter = () => Math.random() + 0.5;

export async function withRetry<T>(operation: () => Promise<T>, config: RetryConfig): Promise<T> {
  let attempt = 0;
  let lastError: unknown;

  while (attempt < config.maxAttempts) {
    try {
      return await operation();
    } catch (error) {
      lastError = error;
      attempt += 1;
      if (attempt >= config.maxAttempts) {
        break;
      }
      const retryAfterMs = (error as RetryableError | undefined)?.retryAfterMs;
      const backoff = retryAfterMs
        ? retryAfterMs
        : Math.min(config.maxDelayMs, config.baseDelayMs * 2 ** (attempt - 1) * jitter());
      await new Promise((resolve) => setTimeout(resolve, backoff));
    }
  }

  throw lastError;
}
