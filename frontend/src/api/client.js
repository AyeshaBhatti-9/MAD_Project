import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// Apne computer ka local IP address dalein (Mobile device se 127.0.0.1 connect nahi hota)
const BASE_URL = 'http://192.168.1.100:8000'; 

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