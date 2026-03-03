import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { message } from 'antd'

const instance: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:12135/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

instance.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    // 如果直接返回数组（如 /filter/domains, /filter/keywords），直接返回
    if (Array.isArray(response.data)) {
      return response.data
    }
    // 后端返回格式: { code: 0, message: "success", data: {...} } 或无 code 的直接数据
    if (response.data?.code === undefined || response.data?.code === 0) {
      return response.data
    }
    // 如果 code 存在且不为 0，视为业务错误
    const errorMessage = response.data.message || '请求失败'
    message.error(errorMessage)
    return Promise.reject(new Error(errorMessage))
  },
  (error) => {
    const errorMessage = error.response?.data?.message || error.message || '请求失败'
    message.error(errorMessage)
    return Promise.reject(error)
  }
)

export default instance

