import React, { useState, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Feather } from '@expo/vector-icons';
import api from '../api/client';
import { AuthContext } from '../context/AuthContext';

export default function SignUpScreen({ navigation }) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useContext(AuthContext);

  const handleBack = () => {
    if (navigation.canGoBack()) {
      navigation.goBack();
    } else {
      navigation.navigate('SignIn');
    }
  };

  const handleSignUp = async () => {
    if (!name || !email || !password) {
      Alert.alert('Error', 'Please fill in all fields.');
      return;
    }

    if (password.length < 8) {
      Alert.alert('Error', 'Password must be at least 8 characters long.');
      return;
    }

    try {
      setLoading(true);
      // const response = await api.post('/auth/signup', { name, email, password });
      // await login(response.data.access_token, response.data.user);

      // Temporary testing mock:
      await login('dummy_mock_token_123', { id: 1, name, email });
      navigation.replace('Home');
    } catch (error) {
      let msg = 'Failed to create account.';
      if (error.response?.status === 409) {
        msg = 'This email is already registered.';
      } else if (error.response?.data?.detail) {
        msg = typeof error.response.data.detail === 'string'
          ? error.response.data.detail
          : error.response.data.detail[0]?.msg;
      }
      Alert.alert('Registration Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  const isFormValid = name.trim() !== '' && email.trim() !== '' && password.length >= 8;

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom', 'left', 'right']}>
      {/* Top Header Bar */}
      <View style={styles.headerBar}>
        <TouchableOpacity 
          style={styles.backButton} 
          onPress={handleBack}
          hitSlop={{ top: 15, bottom: 15, left: 15, right: 15 }}
          activeOpacity={0.7}
        >
          <Feather name="chevron-left" size={24} color="#0A251D" />
        </TouchableOpacity>

        <View style={styles.headerBrand}>
          <View style={styles.brandIcon}>
            <Text style={styles.brandIconText}>Q</Text>
          </View>
          <View>
            <Text style={styles.brandTitle}>QanoonSahib</Text>
            <Text style={styles.brandSub}>Pakistan labour law, made clear</Text>
          </View>
        </View>
      </View>

      <View style={styles.content}>
        {/* User Outline Icon */}
        <View style={styles.userIconCircle}>
          <Feather name="user" size={26} color="#0D4A38" />
        </View>

        <Text style={styles.title}>Create your account</Text>
        <Text style={styles.subtitle}>Save your questions and answers so you can return to them later.</Text>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Name</Text>
          <TextInput
            style={styles.input}
            placeholder="Your name"
            placeholderTextColor="#9EAFA8"
            value={name}
            onChangeText={setName}
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Email address</Text>
          <TextInput
            style={styles.input}
            placeholder="name@example.com"
            placeholderTextColor="#9EAFA8"
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
          />
        </View>

        <View style={styles.formGroup}>
          <Text style={styles.label}>Password</Text>
          <TextInput
            style={styles.input}
            placeholder="Create a password"
            placeholderTextColor="#9EAFA8"
            value={password}
            onChangeText={setPassword}
            secureTextEntry
          />
          <Text style={styles.ruleText}>At least 8 characters</Text>
        </View>

        <TouchableOpacity 
          style={[styles.submitButton, (!isFormValid || loading) && styles.submitButtonDisabled]}
          onPress={handleSignUp}
          disabled={!isFormValid || loading}
          activeOpacity={0.8}
        >
          {loading ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={[styles.submitButtonText, !isFormValid && styles.submitButtonTextDisabled]}>Create account</Text>
          )}
        </TouchableOpacity>

        <View style={styles.footerLinkRow}>
          <Text style={styles.footerLinkMuted}>Already have an account? </Text>
          <TouchableOpacity onPress={() => navigation.navigate('SignIn')}>
            <Text style={styles.footerLinkBold}>Sign in</Text>
          </TouchableOpacity>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 20,
  },
  headerBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#EEF2F0',
  },
  backButton: {
    width: 38,
    height: 38,
    borderRadius: 19,
    borderWidth: 1,
    borderColor: '#CED7D3',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
    backgroundColor: '#FFFFFF',
  },
  headerBrand: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  brandIcon: {
    width: 32,
    height: 32,
    borderRadius: 8,
    backgroundColor: '#0D4A38',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 8,
  },
  brandIconText: {
    color: '#FFFFFF',
    fontWeight: 'bold',
    fontSize: 16,
  },
  brandTitle: {
    fontWeight: '700',
    fontSize: 15,
    color: '#0A251D',
  },
  brandSub: {
    fontSize: 11,
    color: '#52665F',
  },
  content: {
    marginTop: 20,
    alignItems: 'center',
  },
  userIconCircle: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: '#EAF5EE',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 16,
  },
  title: {
    fontSize: 26,
    fontWeight: 'bold',
    color: '#0A251D',
    marginBottom: 6,
  },
  subtitle: {
    fontSize: 13,
    color: '#52665F',
    textAlign: 'center',
    marginBottom: 18,
    paddingHorizontal: 10,
  },
  formGroup: {
    width: '100%',
    marginBottom: 14,
  },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: '#0A251D',
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderColor: '#CED7D3',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 14,
    backgroundColor: '#FFFFFF',
    color: '#0A251D',
  },
  ruleText: {
    fontSize: 11,
    color: '#B23B3B',
    marginTop: 5,
  },
  submitButton: {
    backgroundColor: '#0D4A38',
    width: '100%',
    paddingVertical: 14,
    borderRadius: 10,
    alignItems: 'center',
    marginTop: 8,
  },
  submitButtonDisabled: {
    backgroundColor: '#E2E8E5',
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontWeight: '600',
    fontSize: 15,
  },
  submitButtonTextDisabled: {
    color: '#8A9B94',
  },
  footerLinkRow: {
    flexDirection: 'row',
    marginTop: 20,
  },
  footerLinkMuted: {
    color: '#52665F',
    fontSize: 13,
  },
  footerLinkBold: {
    color: '#0D4A38',
    fontWeight: 'bold',
    fontSize: 13,
  },
});