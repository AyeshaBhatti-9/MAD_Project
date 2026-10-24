import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Platform } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons, Feather } from '@expo/vector-icons';

export default function OnboardingScreen({ navigation }) {
  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom', 'left', 'right']}>
      {/* Brand Header */}
      <View style={styles.header}>
        <View style={styles.headerLogo}>
          <Text style={styles.headerLogoText}>Q</Text>
        </View>
        <Text style={styles.headerTitle}>QanoonSahib</Text>
      </View>

      {/* Main Hero Content */}
      <View style={styles.content}>
        {/* Shield Icon Box */}
        <View style={styles.shieldIconBox}>
          <MaterialCommunityIcons name="shield-check-outline" size={26} color="#0D4A38" />
        </View>

        {/* Category Badge */}
        <View style={styles.badge}>
          <Text style={styles.badgeText}>KNOW YOUR WORKPLACE RIGHTS</Text>
        </View>

        {/* Main Headline */}
        <Text style={styles.heading}>
          Legal answers should{'\n'}be easy to understand.
        </Text>

        {/* Sub-description */}
        <Text style={styles.description}>
          Ask about Pakistani labour law in your own words and verify every answer through clear legal sources.
        </Text>

        {/* Feature List */}
        <View style={styles.features}>
          <View style={styles.featureItem}>
            <Feather name="message-square" size={16} color="#0D4A38" style={styles.featureIcon} />
            <Text style={styles.featureText}>Ask in simple English</Text>
          </View>
          <View style={styles.featureItem}>
            <Feather name="smartphone" size={16} color="#0D4A38" style={styles.featureIcon} />
            <Text style={styles.featureText}>See the law behind each answer</Text>
          </View>
        </View>
      </View>

      {/* Bottom Actions */}
      <View style={styles.footer}>
        <TouchableOpacity 
          style={styles.primaryButton}
          activeOpacity={0.85}
          onPress={() => navigation.navigate('Home', { guest: true })}
        >
          <View style={styles.buttonContent}>
            <Text style={styles.primaryButtonText}>Ask a question</Text>
            <Feather name="chevron-right" size={18} color="#FFFFFF" style={styles.chevronIcon} />
          </View>
        </TouchableOpacity>
        
        <Text style={styles.subtextGreen}>No account required</Text>

        <TouchableOpacity 
          style={styles.secondaryButton}
          activeOpacity={0.85}
          onPress={() => navigation.navigate('SignIn')}
        >
          <Text style={styles.secondaryButtonText}>Sign in</Text>
        </TouchableOpacity>
        
        <Text style={styles.subtextMuted}>Sign in only if you want to save questions and answers.</Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 24,
    justifyContent: 'space-between',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 8,
  },
  headerLogo: {
    width: 32,
    height: 32,
    backgroundColor: '#0D4A38',
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 10,
  },
  headerLogoText: {
    color: '#FFFFFF',
    fontWeight: '700',
    fontSize: 16,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#0A1C16',
    letterSpacing: -0.2,
  },
  content: {
    marginTop: 10,
  },
  shieldIconBox: {
    width: 50,
    height: 50,
    borderRadius: 14,
    backgroundColor: '#E8F5EE',
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  badge: {
    backgroundColor: '#EBF4F0',
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    marginBottom: 16,
  },
  badgeText: {
    color: '#13543F',
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.7,
  },
  heading: {
    fontSize: 34,
    fontWeight: '700',
    color: '#0A1C16',
    lineHeight: 40,
    letterSpacing: -0.8,
    marginBottom: 16,
  },
  description: {
    fontSize: 14.5,
    color: '#4B6158',
    lineHeight: 22,
    letterSpacing: -0.1,
    marginBottom: 24,
  },
  features: {
    gap: 14,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  featureIcon: {
    marginRight: 10,
  },
  featureText: {
    fontSize: 13.5,
    fontWeight: '500',
    color: '#1C3129',
    letterSpacing: -0.1,
  },
  footer: {
    marginBottom: 16,
    alignItems: 'center',
  },
  primaryButton: {
    backgroundColor: '#0D4A38',
    width: '100%',
    paddingVertical: 15,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  buttonContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '600',
    letterSpacing: -0.2,
  },
  chevronIcon: {
    marginLeft: 6,
  },
  subtextGreen: {
    fontSize: 12.5,
    fontWeight: '600',
    color: '#0D4A38',
    marginTop: 8,
    marginBottom: 10,
  },
  secondaryButton: {
    borderColor: '#CED7D3',
    borderWidth: 1,
    backgroundColor: '#FFFFFF',
    width: '100%',
    paddingVertical: 14,
    borderRadius: 12,
    alignItems: 'center',
  },
  secondaryButtonText: {
    color: '#0D4A38',
    fontSize: 15,
    fontWeight: '600',
    letterSpacing: -0.2,
  },
  subtextMuted: {
    fontSize: 11.5,
    color: '#6E8179',
    marginTop: 8,
    textAlign: 'center',
  },
});