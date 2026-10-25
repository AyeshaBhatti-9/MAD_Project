import React, { useContext } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, SafeAreaView } from 'react-native';
import { AuthContext } from '../context/AuthContext';

export default function HomeScreen({ route, navigation }) {
  const { user, logout } = useContext(AuthContext);
  const isGuest = route.params?.guest || !user;

  const handleSignOut = async () => {
    await logout();
    navigation.replace('Onboarding');
  };

  return (
    <SafeAreaView style={styles.container}>
      <Text style={styles.welcomeText}>
        {isGuest ? 'Welcome, Guest' : `Welcome, ${user?.name}`}
      </Text>
      <Text style={styles.subText}>Chat & Document screens your teammate is building.</Text>

      <TouchableOpacity 
        style={styles.signOutBtn}
        onPress={handleSignOut}
      >
        <Text style={styles.signOutText}>{isGuest ? 'Go to Onboarding' : 'Sign Out'}</Text>
      </TouchableOpacity>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
    backgroundColor: '#FFFFFF',
  },
  welcomeText: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#0D4A38',
    marginBottom: 8,
  },
  subText: {
    fontSize: 14,
    color: '#52665F',
    textAlign: 'center',
    marginBottom: 30,
  },
  signOutBtn: {
    backgroundColor: '#0D4A38',
    paddingHorizontal: 28,
    paddingVertical: 12,
    borderRadius: 8,
  },
  signOutText: {
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
});