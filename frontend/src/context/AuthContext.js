import React, { createContext, useState, useEffect } from 'react';
import * as SecureStore from 'expo-secure-store';
import api from '../api/client';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const token = await SecureStore.getItemAsync('userToken');
      if (token) {
        const response = await api.get('/auth/me');
        setUser(response.data);
      } else {
        setUser(null);
      }
    } catch (error) {
      await SecureStore.deleteItemAsync('userToken');
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (token, userData) => {
    await SecureStore.setItemAsync('userToken', token);
    setUser(userData);
  };

  const logout = async () => {
    await SecureStore.deleteItemAsync('userToken');
    setUser(null);
  };

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
};