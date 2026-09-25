/**
 * Gold Standard Fixture: TypeScript Advanced Symbols (Nested scopes, arrow functions, inheritance)
 */

export function outerFunction(init: string) {
  function innerHelper(count: number): string {
    return init + count
  }
  return innerHelper(42)
}

abstract class BaseClient {
  abstract connect(): void
}

export default class HttpClient extends BaseClient {
  public connect(): void {}
}

export const computeHash = (data: string, ...rest: string[]): string => {
  return data
}

export const useUserProfile = (userId: string) => {
  return { userId }
}

export type ComplexQuery = {
  page: number
  filter?: { name: string }
}
