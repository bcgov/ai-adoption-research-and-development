const apiKey = Deno.env.get("AZURE_DOCUMENT_INTELLIGENCE_API_KEY")!;

/**
 * Polls an Azure operation-location endpoint until it succeeds or fails.
 * @param operationLocation The URL to poll.
 * @param onSuccess Callback invoked with the result when status is 'succeeded'.
 * @param onFailure Callback invoked with the result when status is 'failed'.
 * @param options Optional polling options (intervalMs, logger).
 */
export async function pollOperation<T = any>(
  operationLocation: string,
  onSuccess: (result: T) => Promise<void> | void,
  onFailure?: (result: T) => Promise<void> | void,
  options?: {
    intervalMs?: number;
    logger?: (msg: string) => void;
  }
): Promise<void> {
  const interval = options?.intervalMs ?? 5000;
  const logger = options?.logger ?? console.log;
  const getStatus = ((result: any) => result.status || result.analyzeResult?.status || result.modelInfo?.status);

  let status = "notStarted";
  let result: T;

  // Fetch initial result before entering the loop
  const pollResp = await fetch(operationLocation, {
    headers: { "api-key": apiKey },
  });
  result = await pollResp.json();
  status = getStatus(result);
  logger(`Operation status: ${status}`);
  
  while (status !== "succeeded" && status !== "failed") {
    await new Promise((res) => setTimeout(res, interval));
    const pollResp = await fetch(operationLocation, {
      headers: { "api-key": apiKey },
    });
    result = await pollResp.json();
    status = getStatus(result);
    logger(`Operation status: ${status}`);
  }
  if (status === "succeeded") {
    await onSuccess(result);
  } else if (onFailure) {
    await onFailure(result);
  } else {
    logger("Operation failed:");
    logger(JSON.stringify(result, null, 2));
  }
}
