export class ApiError extends Error {
  status: number
  code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function request<T>(method: string, path: string): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, { method, headers: { Accept: 'application/json' } })
  } catch {
    throw new ApiError(0, 'network', 'Cannot reach the backend. Is it running on port 8000?')
  }
  if (!res.ok) {
    let code = 'error'
    let detail = res.statusText
    try {
      const body = await res.json()
      code = body.error ?? code
      detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string) => request<T>('POST', path),
  del: <T>(path: string) => request<T>('DELETE', path),
}
