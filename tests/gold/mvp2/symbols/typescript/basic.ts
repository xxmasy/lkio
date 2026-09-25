/**
 * Gold Standard Fixture: TypeScript Basic Symbols
 */

export interface UserProfile {
  id: string
  name: string
}

export type UserId = string

export enum UserRole {
  ADMIN = 1,
  USER = 2,
  GUEST = 3
}

export class UserService {
  public static readonly API_VERSION = "v1"
  private endpoint: string

  constructor(endpoint: string) {
    this.endpoint = endpoint
  }

  public async getUser(id: string): Promise<UserProfile> {
    return { id, name: "Alice" }
  }
}

export async function fetchUsers(query?: string): Promise<UserProfile[]> {
  return []
}

export const DEFAULT_PAGE_SIZE = 20
let currentRequestId = 0
