import { get, post } from './client'

export interface User {
  id: string
  email: string
  created_at: string
}

export interface Credentials {
  email: string
  password: string
}

export const authApi = {
  me: () => get<User>('/auth/me'),
  register: (creds: Credentials) => post<User>('/auth/register', creds),
  login: (creds: Credentials) => post<User>('/auth/login', creds),
  logout: () => post<void>('/auth/logout'),
}
