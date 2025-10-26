import { AuthProvider } from "@devfamily/admiral"
import _ from "./request"

export const tokenStorageKey = "admiral_global_admin_session_token"
export const storage = {
  get: (name: string) => {
    return localStorage.getItem(name)
  },
  set: (name: string, value: string) => {
    return localStorage.setItem(name, value)
  },
  remove: (name: string) => {
    return localStorage.removeItem(name)
  }
}

const authProvider = (apiUrl: string): AuthProvider => ({
  login: ({ email, password }) => {
    const url = `${apiUrl}/users/login`
    return _.post(url)({ data: { email, password } }).then((response) => {
      const token = response.token || response.access_token
      if (token) {
        storage.set(tokenStorageKey, token)
      }
      return response
    })
  },
  checkAuth: ({ token }) => {
    const url = `${apiUrl}/users/me`

    if (storage.get(tokenStorageKey)) {
      return _.get(url)({ data: { token } })
    } else {
      return Promise.reject()
    }
  },
  logout: () => {
    const url = `${apiUrl}/users/logout`
    return _.post(url)()
      .then(() => {
        storage.remove(tokenStorageKey)
      })
      .catch(() => {
        // Even if logout fails on server, remove token locally
        storage.remove(tokenStorageKey)
      })
  },
  getIdentity: () => {
    const url = `${apiUrl}/users/me`

    return _.get(url)()
      .catch(() => {
        storage.remove(tokenStorageKey)
        return Promise.reject(new Error("Your session has expired. Please login again."))
      })
      .then((user) => {
        return {
          ...user,
          fullName: user.name || user.telegram_alias || "User",
          tg_alias: user.telegram_alias || user.tg_alias || user.tgAlias
        }
      })
  }
})

export default authProvider
