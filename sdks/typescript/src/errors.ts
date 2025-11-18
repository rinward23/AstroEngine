export class ApiError extends Error {
  public readonly code: string;
  public readonly httpStatus: number;
  public readonly details?: Record<string, unknown>;

  constructor(options: { code: string; httpStatus: number; message: string; details?: Record<string, unknown> }) {
    super(options.message);
    this.name = "ApiError";
    this.code = options.code;
    this.httpStatus = options.httpStatus;
    this.details = options.details;
  }
}

export class RateLimitedError extends ApiError {}
export class InvalidBodyError extends ApiError {}

export function isRateLimited(error: unknown): error is RateLimitedError {
  return error instanceof RateLimitedError;
}

export function isInvalidBody(error: unknown): error is InvalidBodyError {
  return error instanceof InvalidBodyError;
}
