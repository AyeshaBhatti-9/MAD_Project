import React, { useEffect, useContext, useRef } from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AuthContext } from '../context/AuthContext';

export default function SplashScreen({ navigation }) {
  const { user, isLoading } = useContext(AuthContext);
  const progressAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    // 0 se 100 tak smooth loading animation
    Animated.timing(progressAnim, {
      toValue: 1,
      duration: 2000,
      useNativeDriver: false,
    }).start();
  }, []);

  useEffect(() => {
    if (!isLoading) {
      const timer = setTimeout(() => {
        if (user) {
          navigation.replace('Home');
        } else {
          navigation.replace('Onboarding');
        }
      }, 2200);
      return () => clearTimeout(timer);
    }
  }, [isLoading, user]);

  const progressBarWidth = progressAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        {/* Q Logo Box */}
        <View style={styles.logoBox}>
          <Text style={styles.logoText}>Q</Text>
        </View>

        <Text style={styles.title}>QanoonSahib</Text>
        <Text style={styles.subtitle}>Pakistan labour law, made clear.</Text>

        {/* Animated Progress Bar */}
        <View style={styles.loaderContainer}>
          <View style={styles.loaderTrack}>
            <Animated.View style={[styles.loaderBar, { width: progressBarWidth }]} />
          </View>
        </View>
      </View>

      <Text style={styles.footerText}>ASK SIMPLY • UNDERSTAND CLEARLY • VERIFY THE LAW</Text>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0D4A38',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 30,
  },
  content: {
    alignItems: 'center',
    justifyContent: 'center',
    flex: 1,
  },
  logoBox: {
    width: 84,
    height: 84,
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  logoText: {
    fontSize: 44,
    fontWeight: 'bold',
    color: '#0D4A38',
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#FFFFFF',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: '#D1E7DD',
    marginBottom: 32,
  },
  loaderContainer: {
    width: 140,
    height: 4,
  },
  loaderTrack: {
    width: '100%',
    height: '100%',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    borderRadius: 2,
    overflow: 'hidden',
  },
  loaderBar: {
    height: '100%',
    backgroundColor: '#E0A938',
    borderRadius: 2,
  },
  footerText: {
    color: '#A2C5B8',
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 1,
  },
});