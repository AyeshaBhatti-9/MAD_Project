import React, { useCallback, useContext, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator, Alert, Keyboard, KeyboardAvoidingView, Platform, ScrollView,
  StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import * as DocumentPicker from 'expo-document-picker';
import api from '../api/client';
import { AuthContext } from '../context/AuthContext';

const C = {
  green: '#0D4A38', dark: '#0A251D', muted: '#52665F', border: '#E1E8E4',
  pale: '#EAF5EE', bg: '#F6F8F6', white: '#FFFFFF', gold: '#E0A938',
};
const topics = [
  ['briefcase', 'Employment contracts', 'employment contracts'],
  ['clock', 'Wages & overtime', 'wages and overtime'],
  ['book-open', 'Leave & holidays', 'leave and holidays'],
  ['shield', 'Termination', 'termination'],
];

function BrandHeader({ onProfile }) {
  return (
    <View style={s.header}>
      <View style={s.brandMark}><Text style={s.brandQ}>Q</Text></View>
      <View style={{ flex: 1 }}>
        <Text style={s.brandTitle}>QanoonSahib</Text>
        <Text style={s.brandSub}>Pakistan labour law, made clear</Text>
      </View>
      <TouchableOpacity style={s.profileButton} onPress={onProfile} accessibilityLabel="Open profile">
        <Feather name="user" size={19} color={C.green} />
      </TouchableOpacity>
    </View>
  );
}

function PrimaryButton({ title, onPress, disabled, loading, icon }) {
  return (
    <TouchableOpacity onPress={onPress} disabled={disabled || loading} activeOpacity={0.82} style={[s.primary, (disabled || loading) && { opacity: 0.58 }]}>
      {loading ? (
        <ActivityIndicator color={C.white} />
      ) : (
        <>
          {icon ? <Feather name={icon} size={17} color={C.white} /> : null}
          <Text style={s.primaryText}>{title}</Text>
        </>
      )}
    </TouchableOpacity>
  );
}

function PageHeading({ icon, title, subtitle }) {
  return (
    <View style={s.pageHeading}>
      <View style={s.pageIcon}><Feather name={icon} size={22} color={C.green} /></View>
      <View style={{ flex: 1 }}>
        <Text style={s.pageTitle}>{title}</Text>
        <Text style={s.pageSubtitle}>{subtitle}</Text>
      </View>
    </View>
  );
}

function HomeTab({ onAsk, onDocuments, onProfile, question, setQuestion }) {
  return (
    <>
      <BrandHeader onProfile={onProfile} />
      <ScrollView contentContainerStyle={s.homeContent} keyboardShouldPersistTaps="handled">
        <Text style={s.eyebrow}>YOUR RIGHTS, EXPLAINED SIMPLY</Text>
        <Text style={s.heroTitle}>Understand Pakistani labour law with confidence.</Text>
        <Text style={s.body}>Ask a question in your own words. Get a clear answer grounded in legal sources.</Text>
        <View style={s.askCard}>
          <Text style={s.askLabel}>What would you like to understand?</Text>
          <TextInput value={question} onChangeText={setQuestion} onSubmitEditing={() => onAsk(question)} placeholder="e.g. Can my employer make me work on Sunday?" placeholderTextColor="#84938C" multiline style={s.questionInput} />
          <View style={s.askFooter}>
            <View style={s.meta}>
              <Feather name="shield" size={14} color={C.green} />
              <Text style={s.metaText}>No account required</Text>
            </View>
            <Text style={s.metaText}>Simple English</Text>
          </View>
          <TouchableOpacity onPress={() => onAsk(question)} disabled={!question.trim()} style={[s.sendButton, !question.trim() && { backgroundColor: '#C8D2CD' }]} accessibilityLabel="Send question">
            <Feather name="arrow-up" size={19} color={C.white} />
          </TouchableOpacity>
        </View>
        <TouchableOpacity style={s.uploadAction} onPress={onDocuments} activeOpacity={0.8}>
          <View style={s.smallIcon}><Feather name="upload-cloud" size={19} color={C.green} /></View>
          <View style={{ flex: 1 }}>
            <Text style={s.actionTitle}>Upload an employment contract</Text>
            <Text style={s.actionSub}>Ask questions about a PDF</Text>
          </View>
          <Feather name="chevron-right" size={19} color={C.muted} />
        </TouchableOpacity>
        <View style={s.sectionHead}>
          <Text style={s.sectionTitle}>Popular topics</Text>
          <Text style={s.mutedSmall}>Tap to ask</Text>
        </View>
        <View style={s.topicGrid}>
          {topics.map(([icon, label, topic]) => (
            <TouchableOpacity key={label} style={s.topicCard} onPress={() => onAsk(`What are my rights about ${topic}?`)}>
              <View style={s.smallIcon}><Feather name={icon} size={17} color={C.green} /></View>
              <Text style={s.topicText}>{label}</Text>
              <Feather name="chevron-right" size={15} color={C.muted} />
            </TouchableOpacity>
          ))}
        </View>
        <View style={s.trust}>
          <Feather name="book-open" size={20} color={C.green} />
          <Text style={s.trustText}>
            <Text style={{ fontWeight: '700' }}>Grounded in law. </Text>
            Answers include sections from supported Pakistani labour-law sources.
          </Text>
        </View>
      </ScrollView>
    </>
  );
}

function CitationCard({ citation, expanded, onToggle, onLayout }) {
  const section = [citation.section_number && citation.section_number !== 'N/A' ? `Section ${citation.section_number}` : '', citation.section_title].filter(Boolean).join(' · ') || 'Legal provision';
  return <View style={s.citation} onLayout={onLayout}>
    <TouchableOpacity onPress={onToggle} activeOpacity={0.7} style={s.citationHead} accessibilityLabel={expanded ? 'Collapse source' : 'Expand source'}>
      <View style={s.citationNumber}><Text style={s.citationNumText}>{citation.index}</Text></View>
      <View style={{ flex: 1 }}><Text style={s.citationLaw}>{citation.law_name || 'Legal source'}</Text><Text style={s.citationSection}>{section}</Text></View>
      <Feather name={expanded ? 'chevron-up' : 'chevron-down'} size={17} color={C.muted} />
    </TouchableOpacity>
    {expanded ? <>
      <Text style={s.excerpt}>{citation.excerpt}</Text>
      {Boolean(citation.why_relevant) && <Text style={s.why}>{citation.why_relevant}</Text>}
    </> : null}
  </View>;
}

function AnswerText({ content, citations, onCitation }) {
  const citationByIndex = new Map((citations || []).map(item => [String(item.index), item]));
  const parts = String(content || '').split(/(\[\d+\])/g);
  return (
    <Text style={s.answerBody}>
      {parts.map((part, index) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (!match || !citationByIndex.has(match[1])) return <Text key={index}>{part}</Text>;
        const citation = citationByIndex.get(match[1]);
        return <Text key={index} onPress={() => onCitation(citation)} style={s.inlineCitation}>{part}</Text>;
      })}
    </Text>
  );
}

function ChatTab({ messages, busy, onAsk, onBackHome, contractName, onCitation }) {
  const [draft, setDraft] = useState('');
  const [keyboardHeight, setKeyboardHeight] = useState(0);
  const insets = useSafeAreaInsets();
  const scrollRef = useRef(null);

  const [collapsed, setCollapsed] = useState({});   // key -> true when collapsed
  const answerY = useRef({});                        // message index -> y of answer card
  const citationY = useRef({});                      // "msg-cite" key -> y inside answer card

  function toggleCitation(key) {
    setCollapsed(prev => ({ ...prev, [key]: !prev[key] }));
  }

  function jumpToCitation(messageIndex, citation) {
    const key = `${messageIndex}-${citation.index}`;
    setCollapsed(prev => ({ ...prev, [key]: false }));          // make sure it's open
    const y = (answerY.current[messageIndex] || 0) + (citationY.current[key] || 0);
    scrollRef.current?.scrollTo({ y: Math.max(y - 12, 0), animated: true });
  }

  useEffect(() => {
    const show = Keyboard.addListener('keyboardDidShow', e => {
      setKeyboardHeight(e.endCoordinates.height);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 50);
    });
    const hide = Keyboard.addListener('keyboardDidHide', () => setKeyboardHeight(0));
    return () => { show.remove(); hide.remove(); };
  }, []);

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, paddingBottom: Platform.OS === 'android' ? keyboardHeight : 0 }}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={s.chatHeader}>
        <TouchableOpacity onPress={onBackHome} style={s.backCircle}>
          <Feather name="chevron-left" size={22} color={C.dark} />
        </TouchableOpacity>
        <View>
          <Text style={s.chatTitle}>Labour-law answer</Text>
          <View style={s.chatSubRow}>
            <View style={s.onlineDot} />
            <Text style={s.chatSub}>Sources checked</Text>
          </View>
        </View>
      </View>
      <ScrollView ref={scrollRef} style={s.chatScroll} contentContainerStyle={{ padding: 16, paddingBottom: 20 }} keyboardShouldPersistTaps="handled">
        <Text style={s.dateLabel}>Today</Text>
        {contractName ? (
          <View style={s.attachment}>
            <Feather name="file-text" size={19} color={C.green} />
            <View style={{ flex: 1 }}>
              <Text style={s.attachmentOverline}>ATTACHED CONTRACT</Text>
              <Text style={s.attachmentName} numberOfLines={1}>{contractName}</Text>
            </View>
          </View>
        ) : null}
        {messages.map((message, index) => message.role === 'user' ? (
          <View key={`${index}-u`} style={s.userBubble}>
            <Text style={s.userBubbleText}>{message.content}</Text>
          </View>
        ) : (
          <View key={`${index}-a`} style={s.answerCard} onLayout={e => { answerY.current[index] = e.nativeEvent.layout.y; }}>
            <View style={s.answerTitleRow}>
              <View style={s.answerMark}>
                <MaterialCommunityIcons name="scale-balance" size={19} color={C.white} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={s.answerEyebrow}>QANOONSAHIB</Text>
                <Text style={s.answerTitle}>Legal information</Text>
              </View>
              {message.xai?.confidence_label ? <Text style={[s.confidence, message.xai.confidence_label === 'Low' && s.lowConfidence]}>{message.xai.confidence_label} confidence</Text> : null}
            </View>
            <AnswerText content={message.content} citations={message.citations} onCitation={c => jumpToCitation(index, c)} />
            {message.xai?.confidence_label === 'Low' ? <Text style={s.lowHint}>The retrieved sources may be a weak match. Please verify with a qualified lawyer.</Text> : null}
            {message.citations?.length ? (
              <>
                <View style={s.sourceTitleRow}>
                  <Text style={s.sourceTitle}>Legal sources</Text>
                  <Text style={s.mutedSmall}>{message.citations.length} cited</Text>
                </View>
                {message.citations.map(c => {
                  const key = `${index}-${c.index}`;
                  return <CitationCard
                    key={key}
                    citation={c}
                    expanded={!collapsed[key]}
                    onToggle={() => toggleCitation(key)}
                    onLayout={e => { citationY.current[key] = e.nativeEvent.layout.y; }}
                  />;
                })}
              </>
            ) : null}
            <View style={s.disclaimer}>
              <Feather name="info" size={15} color="#75571C" />
              <Text style={s.disclaimerText}>This is general legal information, not legal advice. For your specific situation, consult a qualified labour lawyer.</Text>
            </View>
          </View>
        ))}
        {busy ? (
          <View style={s.loadingAnswer}>
            <ActivityIndicator color={C.green} />
            <Text style={s.loadingText}>Checking legal sources…</Text>
          </View>
        ) : null}
      </ScrollView>
      <View style={s.composerWrap}>
        <View style={s.composer}>
          <TextInput value={draft} onChangeText={setDraft} placeholder={messages.length ? 'Ask a follow-up question…' : 'Ask about this contract…'} placeholderTextColor="#74827B" multiline style={s.composerInput} />
          <TouchableOpacity disabled={!draft.trim() || busy} onPress={() => { const value = draft; setDraft(''); onAsk(value); }} style={[s.composerSend, (!draft.trim() || busy) && { opacity: 0.5 }]}>
            <Feather name="arrow-up" size={19} color={C.white} />
          </TouchableOpacity>
        </View>
        <Text style={s.composerHint}>{messages.length ? 'Ask a follow-up about this answer' : 'Ask your first question about this contract'}</Text>
      </View>
    </KeyboardAvoidingView>
  );
}

function DocumentsTab({ sessionDocument, documents, loading, uploading, onUpload, onRemove, onAskContract, signedIn, onRefresh, onProfile, onOpenDocument }) {
  return (
    <>
      <BrandHeader onProfile={onProfile} />
      <ScrollView contentContainerStyle={s.screenContent} onScrollBeginDrag={onRefresh}>
        <PageHeading icon="file-text" title="Your documents" subtitle="Ask questions about your employment contract." />
        {sessionDocument ? (
          <View style={s.docCard}>
            <View style={s.pdfBadge}><Text style={s.pdfText}>PDF</Text></View>
            <View style={{ flex: 1 }}>
              <Text style={s.docName} numberOfLines={1}>{sessionDocument.filename}</Text>
              <Text style={s.docMeta}>{sessionDocument.saved ? 'Saved to your account' : 'Current session only'} · {sessionDocument.char_count?.toLocaleString()} characters</Text>
            </View>
            <TouchableOpacity onPress={onRemove}><Text style={s.removeText}>Remove</Text></TouchableOpacity>
          </View>
        ) : null}
        {!sessionDocument ? (
          <View style={s.uploadPanel}>
            <View style={s.largeUpload}><Feather name="upload-cloud" size={26} color={C.green} /></View>
            <Text style={s.uploadTitle}>Upload employment contract</Text>
            <Text style={s.uploadDescription}>Upload a PDF to ask questions about your contract alongside relevant labour laws.</Text>
            <PrimaryButton title="Select PDF" onPress={onUpload} loading={uploading} icon="upload" />
            <Text style={s.mutedSmall}>PDF only · Up to 5 MB</Text>
          </View>
        ) : (
          <PrimaryButton title="Ask about this contract" onPress={onAskContract} icon="message-square" />
        )}
        <View style={s.privacyCard}>
          <Feather name="shield" size={20} color={C.green} />
          <Text style={s.privacyText}>{signedIn ? 'Your uploaded contract is saved to your account and used to answer your questions.' : 'Signed-out uploads are available only during this session.'}</Text>
        </View>
        {signedIn ? (
          <>
            <View style={s.sectionHead}>
              <Text style={s.sectionTitle}>Saved documents</Text>
              <TouchableOpacity onPress={onRefresh}><Feather name="refresh-cw" size={16} color={C.green} /></TouchableOpacity>
            </View>
            {loading ? <ActivityIndicator color={C.green} /> : documents.map(doc => (
              <TouchableOpacity key={doc.id} onPress={() => onOpenDocument(doc)} style={s.listRow}>
                <View style={s.pdfBadge}><Text style={s.pdfText}>PDF</Text></View>
                <View style={{ flex: 1 }}>
                  <Text style={s.docName} numberOfLines={1}>{doc.filename}</Text>
                  <Text style={s.docMeta}>{doc.char_count?.toLocaleString()} characters</Text>
                </View>
                <Feather name="chevron-right" size={18} color={C.muted} />
              </TouchableOpacity>
            ))}
          </>
        ) : null}
      </ScrollView>
    </>
  );
}

function SavedTab({ items, loading, onOpen, onSignIn, onAsk, signedIn, onRefresh, onProfile }) {
  return (
    <>
      <BrandHeader onProfile={onProfile} />
      <ScrollView contentContainerStyle={s.screenContent} onScrollBeginDrag={onRefresh}>
        <PageHeading icon="message-square" title="My questions" subtitle="Your saved questions and answers." />
        {!signedIn ? (
          <View style={s.emptyCard}>
            <View style={s.emptyIcon}><Feather name="message-square" size={27} color={C.green} /></View>
            <Text style={s.emptyTitle}>Save your legal questions</Text>
            <Text style={s.emptyBody}>Sign in to keep questions and answers across sessions.</Text>
            <PrimaryButton title="Sign in to save questions" onPress={onSignIn} />
            <Text style={s.emptyFoot}>You can ask without signing in, too.</Text>
          </View>
        ) : loading ? (
          <ActivityIndicator color={C.green} />
        ) : items.length ? (
          items.map(item => (
            <TouchableOpacity key={item.id} onPress={() => onOpen(item)} style={s.savedRow}>
              <View style={{ flex: 1 }}>
                <Text style={s.savedQuestion} numberOfLines={2}>{item.title}</Text>
                <Text style={s.docMeta}>{new Date(`${item.updated_at}${/Z|[+-]\d\d:\d\d$/.test(item.updated_at) ? '' : 'Z'}`).toLocaleDateString()}</Text>
              </View>
              <Feather name="chevron-right" size={18} color={C.green} />
            </TouchableOpacity>
          ))
        ) : (
          <View style={s.emptyCard}>
            <View style={s.emptyIcon}><Feather name="message-square" size={27} color={C.green} /></View>
            <Text style={s.emptyTitle}>No saved questions yet</Text>
            <Text style={s.emptyBody}>Questions you ask while signed in will appear here.</Text>
            <PrimaryButton title="Ask a question" onPress={onAsk} />
          </View>
        )}
      </ScrollView>
    </>
  );
}

function HelpTab({ onProfile }) {
  const items = [['What can I ask?', 'Questions about employment and labour law in Pakistan.'], ['Where do answers come from?', 'Supported legal sources are shown with every answer.'], ['Is this legal advice?', 'No. For advice about your situation, consult a qualified lawyer.']];
  return (
    <>
      <BrandHeader onProfile={onProfile} />
      <ScrollView contentContainerStyle={s.screenContent}>
        <PageHeading icon="help-circle" title="Help & about" subtitle="How QanoonSahib works." />
        <View style={s.principle}>
          <Text style={s.principleOverline}>OUR PRINCIPLE</Text>
          <Text style={s.principleText}>Ask simply. Understand clearly. Verify the law.</Text>
        </View>
        {items.map(([title, body]) => (
          <View key={title} style={s.helpItem}>
            <Text style={s.helpTitle}>{title}</Text>
            <Text style={s.helpBody}>{body}</Text>
          </View>
        ))}
      </ScrollView>
    </>
  );
}

export default function MainAppScreen({ navigation }) {
  const { user, logout } = useContext(AuthContext);
  const [tab, setTab] = useState('home');
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [conversationId, setConversationId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [sessionDocument, setSessionDocument] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [conversations, setConversations] = useState([]);
  const [loadingList, setLoadingList] = useState(false);
  const [uploading, setUploading] = useState(false);

  const refreshDocuments = useCallback(async () => {
    if (!user) return;
    setLoadingList(true);
    try {
      const response = await api.get('/documents');
      setDocuments(response.data);
    } catch (error) {
      Alert.alert('Could not load documents', getError(error));
    } finally {
      setLoadingList(false);
    }
  }, [user]);

  const refreshConversations = useCallback(async () => {
    if (!user) return;
    setLoadingList(true);
    try {
      const response = await api.get('/chat/conversations');
      setConversations(response.data);
    } catch (error) {
      Alert.alert('Could not load questions', getError(error));
    } finally {
      setLoadingList(false);
    }
  }, [user]);

  async function ask(nextQuestion) {
    const value = String(nextQuestion || '').trim();
    if (!value || busy) return;
    setQuestion('');
    const prior = messages;
    setMessages(current => [...current, { role: 'user', content: value }]);
    setTab('chat');
    setBusy(true);
    try {
      const body = { question: value };
      if (conversationId) body.conversation_id = conversationId;
      else if (!user && prior.length) body.history = prior.slice(-12).map(({ role, content }) => ({ role, content }));
      if (sessionDocument) {
        if (user && sessionDocument.id != null) body.document_id = sessionDocument.id;
        else body.session_document = sessionDocument.extracted_text;
      }
      const response = await api.post('/chat/ask', body);
      if (response.data.conversation_id != null) setConversationId(response.data.conversation_id);
      setMessages(current => [...current, { role: 'assistant', content: response.data.answer, citations: response.data.citations || [], xai: response.data.xai }]);
    } catch (error) {
      const message = getError(error);
      setMessages(current => [...current, { role: 'assistant', content: `I couldn't get an answer right now. ${message}`, citations: [], xai: null }]);
    } finally {
      setBusy(false);
    }
  }

  async function pickAndUpload() {
    try {
      const result = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true, multiple: false });
      if (result.canceled) return;
      const file = result.assets[0];
      if (!file.name.toLowerCase().endsWith('.pdf')) { Alert.alert('PDF required', 'Please choose a PDF file.'); return; }
      if (file.size && file.size > 5 * 1024 * 1024) { Alert.alert('File too large', 'Choose a PDF smaller than 5 MB.'); return; }
      const data = new FormData();
      data.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/pdf' });
      setUploading(true);
      const response = await api.post('/documents/upload', data, { headers: { 'Content-Type': 'multipart/form-data' } });
      setSessionDocument(response.data);
      setTab('documents');
      if (user) refreshDocuments();
    } catch (error) {
      if (error?.code !== 'ERR_CANCELED') Alert.alert('Upload failed', getError(error));
    } finally {
      setUploading(false);
    }
  }

  function startContractChat() {
    setMessages([]);
    setConversationId(null);
    setTab('chat');
  }

  async function openConversation(item) {
    try {
      setBusy(true);
      const response = await api.get(`/chat/conversations/${item.id}`);
      setMessages(response.data.messages.map(message => ({ role: message.role, content: message.content, citations: message.citations || [], xai: message.xai })));
      setConversationId(item.id);
      setSessionDocument(null);
      setTab('chat');
    } catch (error) {
      Alert.alert('Could not open question', getError(error));
    } finally {
      setBusy(false);
    }
  }

  async function openSavedDocument(item) {
    try {
      const response = await api.get(`/documents/${item.id}`);
      setSessionDocument({ ...response.data, saved: true });
      setTab('documents');
    } catch (error) {
      Alert.alert('Could not open document', getError(error));
    }
  }

  const openProfile = () => user
    ? Alert.alert(user.name, user.email, [{ text: 'Cancel', style: 'cancel' }, { text: 'Sign out', style: 'destructive', onPress: handleSignOut }])
    : navigation.navigate('SignIn');

  function changeTab(nextTab) {
    setTab(nextTab);
    if (nextTab === 'saved') refreshConversations();
    if (nextTab === 'documents') refreshDocuments();
  }

  function startNewChat() {
    setMessages([]);
    setConversationId(null);
    setTab('home');
  }

  async function handleSignOut() {
    await logout();
    setMessages([]);
    setConversationId(null);
    setSessionDocument(null);
    navigation.replace('Onboarding');
  }

  return (
    <SafeAreaView style={s.container} edges={['top', 'bottom', 'left', 'right']}>
      {tab === 'home' && <HomeTab onAsk={ask} onDocuments={() => setTab('documents')} onProfile={openProfile} question={question} setQuestion={setQuestion} />}
      {tab === 'chat' && <ChatTab messages={messages} busy={busy} onAsk={ask} onBackHome={startNewChat} contractName={sessionDocument?.filename} onCitation={citation => Alert.alert(`${citation.law_name}${citation.section_number ? ` · Section ${citation.section_number}` : ''}`, citation.excerpt || citation.why_relevant || 'Legal source')} />}
      {tab === 'documents' && <DocumentsTab sessionDocument={sessionDocument} documents={documents} loading={loadingList} uploading={uploading} onUpload={pickAndUpload} onRemove={() => setSessionDocument(null)} onAskContract={startContractChat} signedIn={Boolean(user)} onRefresh={refreshDocuments} onProfile={openProfile} onOpenDocument={openSavedDocument} />}
      {tab === 'saved' && <SavedTab items={conversations} loading={loadingList} onOpen={openConversation} onSignIn={() => navigation.navigate('SignIn')} onAsk={startNewChat} signedIn={Boolean(user)} onRefresh={refreshConversations} onProfile={openProfile} />}
      {tab === 'help' && <HelpTab onProfile={openProfile} />}
      {tab !== 'chat' && (
        <View style={s.tabBar}>
          {[['home', 'Home', 'home'], ['saved', 'My questions', 'message-square'], ['documents', 'Documents', 'file-text'], ['help', 'Help', 'help-circle']].map(([key, label, icon]) => (
            <TouchableOpacity key={key} onPress={() => changeTab(key)} style={[s.tabItem, tab === key && s.tabActive]}>
              <Feather name={icon} size={19} color={tab === key ? C.green : C.muted} />
              <Text style={[s.tabLabel, tab === key && { color: C.green }]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      )}
    </SafeAreaView>
  );
}

function getError(error) {
  const data = error?.response?.data;
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map(item => item.msg).join('\n');
  if (data?.error) return data.error;
  return error?.message || 'Please try again in a moment.';
}

const s = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.white },
  header: { minHeight: 62, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 17, borderBottomWidth: 1, borderBottomColor: '#EDF0EE', gap: 10, backgroundColor: C.white },
  brandMark: { width: 34, height: 34, borderRadius: 10, alignItems: 'center', justifyContent: 'center', backgroundColor: C.green },
  brandQ: { color: C.white, fontWeight: '800', fontSize: 19 },
  brandTitle: { color: C.dark, fontSize: 14, fontWeight: '800' },
  brandSub: { color: C.muted, fontSize: 10, marginTop: 1 },
  profileButton: { width: 38, height: 38, borderRadius: 20, borderWidth: 1, borderColor: C.border, alignItems: 'center', justifyContent: 'center' },
  homeContent: { padding: 18, paddingBottom: 26 },
  eyebrow: { color: C.green, fontSize: 10, fontWeight: '800', letterSpacing: 1.1, marginTop: 16, marginBottom: 10 },
  heroTitle: { color: C.dark, fontSize: 29, lineHeight: 34, fontWeight: '800', letterSpacing: -0.6, marginBottom: 9 },
  body: { color: C.muted, fontSize: 14, lineHeight: 21, marginBottom: 18 },
  askCard: { borderRadius: 18, borderWidth: 1, borderColor: C.border, padding: 15, backgroundColor: C.white, elevation: 2, shadowColor: '#1B342A', shadowOpacity: 0.07, shadowRadius: 12, shadowOffset: { width: 0, height: 5 } },
  askLabel: { color: C.dark, fontSize: 13, fontWeight: '700', marginBottom: 10 },
  questionInput: { minHeight: 76, maxHeight: 120, padding: 0, textAlignVertical: 'top', fontSize: 14, color: C.dark, lineHeight: 20, paddingRight: 46 },
  askFooter: { borderTopWidth: 1, borderColor: '#EDF0EE', paddingTop: 10, marginTop: 8, flexDirection: 'row', justifyContent: 'space-between' },
  meta: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  metaText: { color: C.muted, fontSize: 10, fontWeight: '600' },
  sendButton: { width: 40, height: 40, borderRadius: 12, backgroundColor: C.green, alignItems: 'center', justifyContent: 'center', position: 'absolute', right: 13, bottom: 46 },
  uploadAction: { marginTop: 12, padding: 13, borderWidth: 1, borderColor: C.border, borderRadius: 15, flexDirection: 'row', alignItems: 'center', gap: 10 },
  smallIcon: { width: 36, height: 36, borderRadius: 10, backgroundColor: C.pale, alignItems: 'center', justifyContent: 'center' },
  actionTitle: { color: C.dark, fontWeight: '700', fontSize: 12 },
  actionSub: { color: C.muted, fontSize: 11, marginTop: 3 },
  sectionHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 24, marginBottom: 11 },
  sectionTitle: { color: C.dark, fontSize: 16, fontWeight: '800' },
  mutedSmall: { color: C.muted, fontSize: 11 },
  topicGrid: { gap: 8 },
  topicCard: { minHeight: 58, borderWidth: 1, borderColor: C.border, borderRadius: 14, padding: 9, alignItems: 'center', flexDirection: 'row', gap: 10, backgroundColor: C.white },
  topicText: { flex: 1, color: C.dark, fontSize: 12, fontWeight: '700' },
  trust: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, backgroundColor: C.pale, borderRadius: 14, padding: 14, marginTop: 22 },
  trustText: { flex: 1, color: '#365649', fontSize: 11, lineHeight: 17 },
  tabBar: { minHeight: 64, borderTopWidth: 1, borderTopColor: C.border, flexDirection: 'row', paddingHorizontal: 4, paddingTop: 6, paddingBottom: 4, backgroundColor: C.white },
  tabItem: { flex: 1, borderRadius: 11, alignItems: 'center', justifyContent: 'center', gap: 3 },
  tabActive: { backgroundColor: '#F0F6F3' },
  tabLabel: { color: C.muted, fontSize: 9, fontWeight: '600' },
  screenContent: { padding: 18, paddingBottom: 30 },
  pageHeading: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 13, marginBottom: 22 },
  pageIcon: { width: 47, height: 47, borderRadius: 14, backgroundColor: C.pale, alignItems: 'center', justifyContent: 'center' },
  pageTitle: { fontSize: 21, color: C.dark, fontWeight: '800' },
  pageSubtitle: { color: C.muted, fontSize: 11, marginTop: 3 },
  primary: { minHeight: 47, borderRadius: 13, paddingHorizontal: 15, backgroundColor: C.green, alignItems: 'center', justifyContent: 'center', flexDirection: 'row', gap: 8, marginTop: 4 },
  primaryText: { color: C.white, fontWeight: '700', fontSize: 13 },
  uploadPanel: { alignItems: 'stretch', padding: 22, borderWidth: 1, borderStyle: 'dashed', borderColor: '#BAC8C1', borderRadius: 19, backgroundColor: C.white },
  largeUpload: { width: 58, height: 58, borderRadius: 17, backgroundColor: C.pale, alignItems: 'center', justifyContent: 'center', marginBottom: 14, alignSelf: 'center' },
  uploadTitle: { fontSize: 16, color: C.dark, fontWeight: '800', marginBottom: 7, textAlign: 'center' },
  uploadDescription: { fontSize: 12, lineHeight: 18, color: C.muted, textAlign: 'center', marginBottom: 14 },
  privacyCard: { flexDirection: 'row', gap: 11, padding: 14, borderRadius: 14, backgroundColor: C.pale, marginTop: 16, alignItems: 'flex-start' },
  privacyText: { color: '#4D675C', flex: 1, fontSize: 11, lineHeight: 16 },
  docCard: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 13, borderWidth: 1, borderColor: C.border, borderRadius: 15, marginBottom: 13, backgroundColor: C.white },
  pdfBadge: { width: 40, height: 45, borderRadius: 9, backgroundColor: '#FBE9E5', alignItems: 'center', justifyContent: 'center' },
  pdfText: { color: '#8D3C33', fontWeight: '800', fontSize: 10 },
  docName: { color: C.dark, fontSize: 12, fontWeight: '700' },
  docMeta: { color: C.muted, fontSize: 10, marginTop: 4 },
  removeText: { color: '#8D3C33', fontSize: 11, fontWeight: '700' },
  listRow: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderWidth: 1, borderColor: C.border, borderRadius: 13, marginBottom: 8 },
  emptyCard: { alignItems: 'center', borderWidth: 1, borderColor: C.border, borderRadius: 18, backgroundColor: C.white, padding: 21 },
  emptyIcon: { width: 58, height: 58, borderRadius: 18, backgroundColor: C.pale, alignItems: 'center', justifyContent: 'center', marginBottom: 13 },
  emptyTitle: { color: C.dark, fontSize: 17, fontWeight: '800', textAlign: 'center' },
  emptyBody: { color: C.muted, fontSize: 12, lineHeight: 18, textAlign: 'center', marginVertical: 8 },
  emptyFoot: { color: C.muted, fontSize: 11, marginTop: 10 },
  savedRow: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 15, borderBottomWidth: 1, borderColor: C.border, backgroundColor: C.white },
  savedQuestion: { color: C.dark, fontSize: 13, fontWeight: '700', lineHeight: 18 },
  principle: { backgroundColor: C.green, borderRadius: 17, padding: 20, marginBottom: 16 },
  principleOverline: { color: '#B9D7CC', fontSize: 10, fontWeight: '800', letterSpacing: 1, marginBottom: 9 },
  principleText: { color: C.white, fontSize: 18, fontWeight: '800', lineHeight: 25 },
  helpItem: { padding: 15, borderBottomWidth: 1, borderColor: C.border, backgroundColor: C.white },
  helpTitle: { color: C.dark, fontSize: 13, fontWeight: '700' },
  helpBody: { color: C.muted, fontSize: 12, lineHeight: 18, marginTop: 5 },
  chatHeader: { minHeight: 58, borderBottomWidth: 1, borderColor: C.border, flexDirection: 'row', alignItems: 'center', gap: 11, paddingHorizontal: 14 },
  backCircle: { width: 36, height: 36, borderWidth: 1, borderColor: C.border, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  chatTitle: { color: C.dark, fontSize: 14, fontWeight: '800' },
  chatSubRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 3 },
  chatSub: { color: C.muted, fontSize: 10 },
  onlineDot: { width: 6, height: 6, backgroundColor: '#35A06F', borderRadius: 4 },
  chatScroll: { flex: 1, backgroundColor: '#F4F6F4' },
  dateLabel: { color: C.muted, textAlign: 'center', fontSize: 10, fontWeight: '600', marginBottom: 14 },
  attachment: { flexDirection: 'row', alignItems: 'center', gap: 9, borderWidth: 1, borderColor: C.border, borderRadius: 12, backgroundColor: C.white, padding: 10, marginBottom: 14 },
  attachmentOverline: { color: C.green, fontSize: 9, fontWeight: '800' },
  attachmentName: { color: C.dark, fontSize: 11, fontWeight: '700', marginTop: 2 },
  userBubble: { alignSelf: 'flex-end', maxWidth: '84%', padding: 12, borderRadius: 16, borderBottomRightRadius: 4, backgroundColor: C.green, marginBottom: 13 },
  userBubbleText: { color: C.white, fontSize: 13, lineHeight: 19 },
  answerCard: { borderWidth: 1, borderColor: C.border, borderRadius: 5, borderTopRightRadius: 17, borderBottomLeftRadius: 17, borderBottomRightRadius: 17, backgroundColor: C.white, padding: 14, marginBottom: 16 },
  answerTitleRow: { flexDirection: 'row', alignItems: 'center', gap: 9, borderBottomWidth: 1, borderColor: '#EDF0EE', paddingBottom: 12, marginBottom: 13 },
  answerMark: { width: 35, height: 35, borderRadius: 11, backgroundColor: C.green, alignItems: 'center', justifyContent: 'center' },
  answerEyebrow: { color: C.green, fontSize: 9, letterSpacing: 0.8, fontWeight: '800' },
  answerTitle: { color: C.dark, fontSize: 11, fontWeight: '700', marginTop: 2 },
  confidence: { color: '#17603F', backgroundColor: '#E5F3EB', borderRadius: 11, paddingVertical: 4, paddingHorizontal: 7, fontSize: 9, fontWeight: '800', overflow: 'hidden' },
  lowConfidence: { color: '#75571C', backgroundColor: '#FBF1DA' },
  answerBody: { color: '#35443D', fontSize: 13, lineHeight: 20 },
  inlineCitation: { color: C.green, fontWeight: '800' },
  lowHint: { color: '#75571C', backgroundColor: '#FBF6E9', padding: 9, borderRadius: 9, fontSize: 11, lineHeight: 16, marginTop: 10 },
  sourceTitleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, marginBottom: 5 },
  sourceTitle: { color: C.dark, fontSize: 13, fontWeight: '800' },
  citation: { borderWidth: 1, borderColor: C.border, borderRadius: 12, backgroundColor: '#FBFCFB', padding: 10, marginTop: 7 },
  citationHead: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  citationNumber: { width: 25, height: 25, borderRadius: 7, backgroundColor: C.pale, alignItems: 'center', justifyContent: 'center' },
  citationNumText: { color: C.green, fontSize: 11, fontWeight: '800' },
  citationLaw: { color: C.dark, fontSize: 11, fontWeight: '800' },
  citationSection: { color: C.muted, fontSize: 10, marginTop: 2 },
  excerpt: { color: '#45524C', fontSize: 11, lineHeight: 16, marginTop: 8 },
  why: { color: C.muted, fontSize: 10, lineHeight: 15, marginTop: 6, fontStyle: 'italic' },
  disclaimer: { flexDirection: 'row', gap: 7, borderRadius: 10, backgroundColor: '#FBF6E9', padding: 10, marginTop: 14, alignItems: 'flex-start' },
  disclaimerText: { flex: 1, color: '#67542B', fontSize: 10, lineHeight: 15 },
  loadingAnswer: { flexDirection: 'row', alignItems: 'center', gap: 9, padding: 13, backgroundColor: C.white, borderRadius: 12, alignSelf: 'flex-start' },
  loadingText: { color: C.muted, fontSize: 12 },
  composerWrap: { padding: 10, borderTopWidth: 1, borderColor: C.border, backgroundColor: C.white },
  composer: { flexDirection: 'row', alignItems: 'flex-end', borderRadius: 14, backgroundColor: '#F5F7F5', padding: 7, paddingLeft: 12 },
  composerInput: { flex: 1, minHeight: 38, maxHeight: 88, paddingTop: 8, paddingBottom: 6, color: C.dark, fontSize: 12, textAlignVertical: 'center' },
  composerSend: { width: 38, height: 38, borderRadius: 12, backgroundColor: C.green, alignItems: 'center', justifyContent: 'center' },
  composerHint: { color: C.muted, textAlign: 'center', fontSize: 9, marginTop: 5 },
});