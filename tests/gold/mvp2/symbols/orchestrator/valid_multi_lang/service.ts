export interface UserServiceConfig {
  apiUrl: string;
  timeout?: number;
}

export class UserService {
  constructor(private config: UserServiceConfig) {}

  public async fetchUser(id: string): Promise<any> {
    return { id, name: "test" };
  }
}
