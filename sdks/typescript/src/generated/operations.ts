/* Auto-generated from OpenAPI */
export interface OperationDescriptor {
  readonly method: string;
  readonly path: string;
  readonly operationId: string;
  readonly summary: string;
}

export const operations = [
  {
    "method": "GET",
    "path": "/charts",
    "operationId": "listCharts",
    "summary": "List generated charts"
  },
  {
    "method": "POST",
    "path": "/charts",
    "operationId": "createChart",
    "summary": "Create a new chart"
  },
  {
    "method": "GET",
    "path": "/charts/{chartId}/transits",
    "operationId": "listTransits",
    "summary": "List transits for a chart"
  }
] as const;
