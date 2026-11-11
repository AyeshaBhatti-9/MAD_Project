import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

const BASE_URL = 'http://192.168.18.152:8000'; 

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

api.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('userToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;

export function getErrorMessage(error) {
  const data = error.response?.data;
  const status = error.response?.status;
  if (status === 429) return 'Too many requests. Please wait a minute.';
  if (status === 409) return 'This email is already registered.';
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail[0]?.msg ?? 'Invalid input';
  if (error.code === 'ECONNABORTED') return 'The request timed out. Please try again.';
  if (!error.response) return 'Cannot reach the server. Check your connection.';
  return 'Something went wrong. Please try again.';
}