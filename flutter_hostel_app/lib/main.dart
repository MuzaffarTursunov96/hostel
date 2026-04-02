import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:latlong2/latlong.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' as mb;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:webview_flutter/webview_flutter.dart';

import 'client_catalog.dart';

const String kLanguageKey = 'language';
final ValueNotifier<String> appLang = ValueNotifier<String>('uz');

String normLang(String? lang) => (lang ?? '').toLowerCase() == 'ru' ? 'ru' : 'uz';

String trPair({
  required String ru,
  required String uz,
  String? lang,
}) {
  return normLang(lang ?? appLang.value) == 'ru' ? ru : uz;
}

String friendlyErrorText(String raw, {String? lang}) {
  final l = normLang(lang ?? appLang.value);
  final s = raw.toLowerCase();
  if (s.contains('failed host lookup') || s.contains('socketexception') || s.contains('network is unreachable')) {
    return l == 'ru'
        ? 'Нет интернета. Проверьте сеть и попробуйте снова.'
        : "Internet yo'q. Tarmoqni tekshirib, qayta urinib ko'ring.";
  }
  if (s.contains('timeoutexception') || s.contains('future not completed') || s.contains('timed out')) {
    return l == 'ru'
        ? 'Сервер долго не отвечает. Повторите попытку.'
        : 'Server javobi kechikdi. Qayta urinib ko‘ring.';
  }
  if (s.contains('status 401') || s.contains('unauthorized')) {
    return l == 'ru'
        ? 'Сессия истекла. Войдите снова.'
        : 'Sessiya tugagan. Qaytadan kiring.';
  }
  if (s.contains('status 5')) {
    return l == 'ru'
        ? 'В сервисе временная ошибка. Попробуйте позже.'
        : 'Xizmatda vaqtinchalik xatolik. Keyinroq urinib ko‘ring.';
  }
  if (s.contains('same-day booking') || s.contains('enable hourly booking')) {
    return l == 'ru'
        ? 'Для брони в одну дату включите "Почасовое бронирование".'
        : 'Bir kunda bron qilish uchun "Soatlik bron"ni yoqing.';
  }
  if (s.contains('prepayment required')) {
    return l == 'ru'
        ? 'Требуется предоплата. Укажите минимально необходимую сумму.'
        : "Oldindan to'lov talab qilinadi. Minimal summani kiriting.";
  }
  if (s.contains('room already exists')) {
    return l == 'ru' ? 'Комната с таким номером уже существует.' : 'Bunday raqamli xona allaqachon mavjud.';
  }
  if (s.contains('maximum 12 room images allowed')) {
    return l == 'ru' ? 'Можно загрузить максимум 12 фото на комнату.' : 'Har xona uchun eng ko‘pi 12 ta rasm yuklash mumkin.';
  }
  if (s.contains('admin only')) {
    return l == 'ru' ? 'Действие доступно только администратору.' : 'Bu amal faqat admin uchun.';
  }
  return l == 'ru'
      ? 'Произошла ошибка. Пожалуйста, попробуйте снова.'
      : 'Xatolik yuz berdi. Iltimos, qayta urinib ko‘ring.';
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  try {
    await dotenv.load(fileName: ".env");
  } catch (_) {}
  final prefs = await SharedPreferences.getInstance();
  appLang.value = normLang(prefs.getString(kLanguageKey));
  runApp(const HostelApp());
}

void showAppAlert(
  BuildContext context,
  String text, {
  bool error = false,
}) {
  if (error) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Row(
          children: [
            const Icon(Icons.wifi_off_rounded, color: Color(0xFFDC2626)),
            const SizedBox(width: 8),
            Text(trPair(ru: 'Внимание', uz: 'Diqqat')),
          ],
        ),
        content: Text(
          friendlyErrorText(text),
          style: const TextStyle(height: 1.35),
        ),
        actions: [
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('OK'),
          ),
        ],
      ),
    );
    return;
  }
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(
      content: Text(
        text,
        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
      ),
      backgroundColor: error ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
      behavior: SnackBarBehavior.floating,
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 14),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      duration: const Duration(seconds: 2),
    ),
  );
}

Future<bool> confirmAction(
  BuildContext context, {
  required String title,
  required String message,
  String confirmText = "O'chirish",
  String cancelText = 'Bekor',
}) async {
  final ok = await showDialog<bool>(
    context: context,
    builder: (_) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(cancelText)),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
          onPressed: () => Navigator.pop(context, true),
          child: Text(confirmText),
        ),
      ],
    ),
  );
  return ok == true;
}

class HostelApp extends StatelessWidget {
  const HostelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<String>(
      valueListenable: appLang,
      builder: (_, __, ___) {
        return MaterialApp(
          debugShowCheckedModeBanner: false,
          title: 'Hotel Mobile',
          theme: ThemeData(
            colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF1E88E5)),
            useMaterial3: true,
            scaffoldBackgroundColor: const Color(0xFFF3F5F9),
            appBarTheme: const AppBarTheme(
              backgroundColor: Colors.white,
              foregroundColor: Color(0xFF101828),
              elevation: 0,
              centerTitle: false,
              surfaceTintColor: Colors.transparent,
            ),
            cardTheme: CardThemeData(
              color: Colors.white,
              elevation: 0,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
              margin: EdgeInsets.zero,
            ),
          ),
          home: const LoginScreen(),
        );
      },
    );
  }
}

class PinLockScreen extends StatefulWidget {
  const PinLockScreen({super.key, this.onVerified, this.onSuccess});

  final VoidCallback? onVerified;
  final WidgetBuilder? onSuccess;

  @override
  State<PinLockScreen> createState() => _PinLockScreenState();
}

class _PinLockScreenState extends State<PinLockScreen> {
  static const String pinKey = 'app_pin';
  final _pinCtrl = TextEditingController();
  String? _error;
  bool _busy = false;

  String _tr({required String ru, required String uz}) {
    final lang = appLang.value == 'ru' ? 'ru' : 'uz';
    return lang == 'ru' ? ru : uz;
  }

  @override
  void dispose() {
    _pinCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkPin() async {
    final pin = _pinCtrl.text.trim();
    if (!RegExp(r'^\d{4}$').hasMatch(pin)) {
      setState(() => _error = 'PIN must be 4 digits');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(pinKey) ?? '';
      if (pin == stored) {
        widget.onVerified?.call();
        if (widget.onSuccess != null && mounted) {
          Navigator.of(context).pushReplacement(
            MaterialPageRoute(builder: widget.onSuccess!),
          );
        }
      } else {
        setState(() => _error = _tr(ru: 'Noto‘g‘ri PIN', uz: 'Noto‘g‘ri PIN'));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () async {
            final popped = await Navigator.of(context).maybePop();
            if (!popped && mounted) {
              Navigator.of(context).pushReplacement(
                MaterialPageRoute(builder: (_) => const LoginScreen()),
              );
            }
          },
        ),
      ),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 360),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.lock_outline_rounded, size: 48, color: Color(0xFF1D4ED8)),
                const SizedBox(height: 12),
                Text(_tr(ru: 'PIN kiriting', uz: 'PIN kiriting'),
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                const SizedBox(height: 12),
                TextField(
                  controller: _pinCtrl,
                  keyboardType: TextInputType.number,
                  obscureText: true,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    hintText: '****',
                  ),
                  onSubmitted: (_) => _checkPin(),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 8),
                  Text(_error!, style: const TextStyle(color: Color(0xFFDC2626))),
                ],
                const SizedBox(height: 12),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _busy ? null : _checkPin,
                    child: _busy
                        ? const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                          )
                        : Text(_tr(ru: 'Ochish', uz: 'Ochish')),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key, this.initialEntryMode});

  final String? initialEntryMode;

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  static const String baseApi = 'https://hmsuz.com/api';
  static const Duration requestTimeout = Duration(seconds: 40);

  static const String tokenKey = 'access_token';
  static const String userIdKey = 'user_id';
  static const String isAdminKey = 'is_admin';
  static const String branchIdKey = 'branch_id';
  static const String pinKey = 'app_pin';
  static const String clientVerifiedKey = 'client_verified';
  static const String clientLangKey = 'client_lang';

  final _formKey = GlobalKey<FormState>();
  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _clientEmailController = TextEditingController();
  final _clientCodeController = TextEditingController();
  final _clientPasswordController = TextEditingController();

  bool _loading = false;
  bool _checkingSession = true;
  String? _error;
  String _uiLang = 'uz';
  String _entryMode = 'staff';
  bool _clientBusy = false;
  String? _clientError;
  int _clientStep = 0;
  bool _clientExists = false;
  String? _clientCookie;

  @override
  void initState() {
    super.initState();
    if (widget.initialEntryMode == 'client') {
      _entryMode = 'client';
    }
    _loadPreferredLanguage();
    _restoreSession();
  }

  @override
  void dispose() {
    _usernameController.dispose();
    _passwordController.dispose();
    _clientEmailController.dispose();
    _clientCodeController.dispose();
    _clientPasswordController.dispose();
    super.dispose();
  }

  Future<void> _restoreSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString(tokenKey);
      final branchId = prefs.getInt(branchIdKey);
      if (token == null || token.isEmpty || branchId == null) return;

      final ok = await _validateToken(token);
      if (!ok || !mounted) return;

      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomeScreen(accessToken: token, branchId: branchId),
        ),
      );
    } finally {
      if (mounted) setState(() => _checkingSession = false);
    }
  }

  Future<void> _loadPreferredLanguage() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final lang = normLang(prefs.getString(kLanguageKey));
      if (!mounted) return;
      setState(() => _uiLang = lang);
    } catch (_) {}
  }

  Future<void> _setLoginLanguage(String lang) async {
    lang = normLang(lang);
    if (_uiLang == lang) return;
    setState(() => _uiLang = lang);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(kLanguageKey, lang);
    appLang.value = lang;
  }

  Future<void> _openLoginLangMenu(BuildContext anchor) async {
    final overlay = Overlay.of(anchor).context.findRenderObject() as RenderBox;
    final box = anchor.findRenderObject() as RenderBox?;
    final origin = box?.localToGlobal(Offset.zero, ancestor: overlay) ?? Offset.zero;
    final rect = RelativeRect.fromLTRB(
      origin.dx,
      origin.dy + (box?.size.height ?? 0),
      overlay.size.width - origin.dx - (box?.size.width ?? 0),
      overlay.size.height - origin.dy - (box?.size.height ?? 0),
    );
    final chosen = await showMenu<String>(
      context: anchor,
      position: rect,
      items: [
        CheckedPopupMenuItem(
          checked: _uiLang == 'ru',
          value: 'ru',
          child: const Text('RU'),
        ),
        CheckedPopupMenuItem(
          checked: _uiLang == 'uz',
          value: 'uz',
          child: const Text('UZ'),
        ),
      ],
    );
    if (chosen != null) {
      await _setLoginLanguage(chosen);
    }
  }

  String _tr({required String ru, required String uz}) {
    return _uiLang == 'ru' ? ru : uz;
  }

  Future<void> _openClientGoogleLogin() async {
    final lang = _uiLang == 'ru' ? 'ru' : 'uz';
    final uri = Uri.parse('https://hmsuz.com/auth/google/start?lang=$lang');
    final ok = await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
    if (!ok && mounted) {
      showAppAlert(
        context,
        _tr(
          ru: 'Не удалось открыть Google вход.',
          uz: 'Google kirishni ochib bo‘lmadi.',
        ),
        error: true,
      );
    }
  }

  void _resetClientFlow() {
    _clientEmailController.clear();
    _clientCodeController.clear();
    _clientPasswordController.clear();
    _clientError = null;
    _clientStep = 0;
    _clientExists = false;
    _clientCookie = null;
  }

  String? _extractCookie(String? header) {
    if (header == null || header.isEmpty) return null;
    final first = header.split(';').first.trim();
    return first.isEmpty ? null : first;
  }

  Future<Map<String, dynamic>> _clientPost(String path, Map<String, dynamic> body) async {
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (_clientCookie != null) headers['Cookie'] = _clientCookie!;
    final r = await http
        .post(
          Uri.parse('https://hmsuz.com$path'),
          headers: headers,
          body: jsonEncode(body),
        )
        .timeout(requestTimeout);
    final cookie = _extractCookie(r.headers['set-cookie']);
    if (cookie != null) _clientCookie = cookie;
    final payload = r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
    if (r.statusCode < 200 || r.statusCode >= 300) {
      final msg = (payload is Map<String, dynamic> ? (payload['error'] ?? payload['detail']) : null) ?? 'Request failed';
      throw Exception(msg.toString());
    }
    return payload is Map<String, dynamic> ? payload : <String, dynamic>{'data': payload};
  }

  Future<void> _clientSendCode() async {
    final email = _clientEmailController.text.trim();
    if (email.isEmpty) {
      setState(() => _clientError = _tr(ru: 'Введите email.', uz: 'Email kiriting.'));
      return;
    }
    setState(() {
      _clientBusy = true;
      _clientError = null;
    });
    try {
      await _clientPost('/auth/email/send-code', {'email': email});
      if (!mounted) return;
      setState(() => _clientStep = 1);
      showAppAlert(context, _tr(ru: 'Код отправлен на почту.', uz: 'Kod emailga yuborildi.'));
    } catch (e) {
      if (!mounted) return;
      setState(() => _clientError = friendlyErrorText(e.toString(), lang: _uiLang));
    } finally {
      if (mounted) setState(() => _clientBusy = false);
    }
  }

  Future<void> _clientVerifyCode() async {
    final email = _clientEmailController.text.trim();
    final code = _clientCodeController.text.trim();
    if (email.isEmpty || code.isEmpty) {
      setState(() => _clientError = _tr(ru: 'Введите код.', uz: 'Kod kiriting.'));
      return;
    }
    setState(() {
      _clientBusy = true;
      _clientError = null;
    });
    try {
      await _clientPost('/auth/email/verify-code', {'email': email, 'code': code});
      final status = await _clientPost('/auth/email/account-status', {'email': email});
      final exists = status['exists'] == true;
      if (!mounted) return;
      setState(() {
        _clientExists = exists;
        _clientStep = 2;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _clientError = friendlyErrorText(e.toString(), lang: _uiLang));
    } finally {
      if (mounted) setState(() => _clientBusy = false);
    }
  }

  Future<void> _clientAuth() async {
    final email = _clientEmailController.text.trim();
    final pass = _clientPasswordController.text.trim();
    if (pass.isEmpty) {
      setState(() => _clientError = _tr(ru: 'Введите пароль.', uz: 'Parol kiriting.'));
      return;
    }
    setState(() {
      _clientBusy = true;
      _clientError = null;
    });
    try {
      final path = _clientExists ? '/auth/email/account-login' : '/auth/email/account-register';
      await _clientPost(path, {'email': email, 'password': pass});
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(clientVerifiedKey, true);
      await prefs.setString(clientLangKey, _uiLang);
      await prefs.setString('client_email', email);

      final existingPin = prefs.getString(pinKey) ?? '';
      if (existingPin.trim().isEmpty) {
        final newPin = await _promptSetPin();
        if (newPin == null || !RegExp(r'^\d{4}$').hasMatch(newPin.trim())) {
          final msg = _tr(
            ru: 'Нужно установить PIN.',
            uz: 'PIN o‘rnatish kerak.',
          );
          setState(() => _clientError = msg);
          if (mounted) showAppAlert(context, msg, error: true);
          return;
        }
        await prefs.setString(pinKey, newPin.trim());
      }
      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ClientCatalogScreen(lang: _uiLang),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _clientError = friendlyErrorText(e.toString(), lang: _uiLang));
    } finally {
      if (mounted) setState(() => _clientBusy = false);
    }
  }

  Future<bool> _validateToken(String token) async {
    try {
      final r = await http
          .get(
            Uri.parse('$baseApi/auth/me'),
            headers: {'Authorization': 'Bearer $token'},
          )
          .timeout(requestTimeout);
      return r.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final r = await http
          .post(
            Uri.parse('$baseApi/auth/login'),
            headers: const {'Content-Type': 'application/json'},
            body: jsonEncode({
              'username': _usernameController.text.trim(),
              'password': _passwordController.text,
            }),
          )
          .timeout(requestTimeout);

      final bodyText = r.body;
      if (r.statusCode != 200) {
        final message = _extractError(bodyText) ??
            _tr(
              ru: 'Неверное имя пользователя или пароль',
              uz: "Login yoki parol noto'g'ri",
            );
        final friendly = friendlyErrorText(message, lang: _uiLang);
        setState(() => _error = friendly);
        if (mounted) {
          showAppAlert(context, friendly, error: true);
        }
        return;
      }

      final data = jsonDecode(bodyText) as Map<String, dynamic>;
      final token = (data['access_token'] ?? '').toString();
      final branchIdRaw = data['branch_id'];
      final branchId = branchIdRaw is int
          ? branchIdRaw
          : int.tryParse(branchIdRaw?.toString() ?? '');

      if (token.isEmpty || branchId == null) {
        final msg = _tr(
          ru: 'Вход выполнен, но token/branch_id отсутствует.',
          uz: 'Kirish bajarildi, lekin token/branch_id topilmadi.',
        );
        setState(() => _error = msg);
        if (mounted) showAppAlert(context, msg, error: true);
        return;
      }

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(tokenKey, token);
      await prefs.setInt(branchIdKey, branchId);
      await prefs.setInt(userIdKey, (data['user_id'] as num?)?.toInt() ?? 0);
      await prefs.setBool(isAdminKey, (data['is_admin'] as bool?) ?? false);
      final lang = normLang('${data['language'] ?? _uiLang}');
      await prefs.setString(kLanguageKey, lang);
      appLang.value = lang;

      if (!mounted) return;
      Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => HomeScreen(accessToken: token, branchId: branchId),
        ),
      );
    } on TimeoutException catch (e) {
      final msg = friendlyErrorText(e.toString(), lang: _uiLang);
      setState(() => _error = msg);
      if (mounted) showAppAlert(context, msg, error: true);
    } catch (e) {
      final msg = friendlyErrorText(e.toString(), lang: _uiLang);
      setState(() => _error = msg);
      if (mounted) showAppAlert(context, msg, error: true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  String? _extractError(String body) {
    try {
      final j = jsonDecode(body);
      if (j is Map<String, dynamic>) {
        final d = j['detail'] ?? j['error'];
        if (d is String && d.isNotEmpty) return d;
      }
    } catch (_) {}
    return null;
  }

  Future<void> _maybeOpenClientPin() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final pin = prefs.getString(pinKey) ?? '';
      if (pin.trim().isNotEmpty) {
        if (!mounted) return;
        Navigator.of(context).pushReplacement(
          MaterialPageRoute(
            builder: (_) => PinLockScreen(
              onSuccess: (_) => ClientCatalogScreen(lang: _uiLang),
            ),
          ),
        );
      }
    } catch (_) {}
  }

  Future<String?> _promptSetPin() async {
    final ctrl = TextEditingController();
    String? error;
    final ok = await showDialog<bool>(
      context: context,
      barrierDismissible: false,
      builder: (_) {
        return StatefulBuilder(
          builder: (context, setLocal) {
            return AlertDialog(
              title: Text(_tr(ru: 'Установите PIN', uz: 'PIN o‘rnating')),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  TextField(
                    controller: ctrl,
                    keyboardType: TextInputType.number,
                    obscureText: true,
                    decoration: InputDecoration(
                      hintText: '****',
                      errorText: error,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _tr(ru: 'Минимум 4 цифры', uz: 'Kamida 4 ta raqam'),
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 12),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () {
                    Navigator.pop(context, false);
                  },
                  child: Text(_tr(ru: 'Отмена', uz: 'Bekor')),
                ),
                FilledButton(
                  onPressed: () {
                    final v = ctrl.text.trim();
                    if (!RegExp(r'^\d{4}$').hasMatch(v)) {
                      setLocal(() => error = _tr(ru: 'Слишком короткий PIN', uz: 'PIN juda qisqa'));
                      return;
                    }
                    Navigator.pop(context, true);
                  },
                  child: Text(_tr(ru: 'Сохранить', uz: 'Saqlash')),
                ),
              ],
            );
          },
        );
      },
    );
    if (ok != true) return null;
    return ctrl.text.trim();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          Positioned.fill(
            child: DecoratedBox(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFFEAF2FF),
                    Color(0xFFF8FAFC),
                    Color(0xFFE6F4FF),
                  ],
                ),
              ),
            ),
          ),
          SafeArea(
            child: Center(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 420),
                  child: Container(
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.96),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(color: const Color(0xFFDCE7FF)),
                      boxShadow: const [
                        BoxShadow(
                          color: Color(0x220F172A),
                          blurRadius: 30,
                          offset: Offset(0, 12),
                        ),
                      ],
                    ),
                    child: Form(
                      key: _formKey,
                      child: Stack(
                        children: [
                          Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                height: 58,
                                width: 58,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  gradient: LinearGradient(
                                    colors: [Color(0xFF1D4ED8), Color(0xFF0284C7)],
                                  ),
                                ),
                                alignment: Alignment.center,
                                child: const Text(
                                  'HMS',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w800,
                                    letterSpacing: 0.6,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 12),
                              const Text(
                                'HMS',
                                style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800, letterSpacing: 1.1),
                              ),
                              const SizedBox(height: 6),
                              Text(
                                _tr(
                                  ru: 'Система управления отелем',
                                  uz: 'Hotel boshqaruv tizimi',
                                ),
                                style: const TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w500),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _tr(
                                  ru: 'Войдите, чтобы продолжить',
                                  uz: 'Davom etish uchun kiring',
                                ),
                                style: const TextStyle(color: Color(0xFF475569)),
                              ),
                              const SizedBox(height: 12),
                              SegmentedButton<String>(
                                segments: [
                                  ButtonSegment<String>(
                                    value: 'staff',
                                    icon: const Icon(Icons.badge_outlined),
                                    label: Text(_tr(ru: 'Сотрудник', uz: 'Xodim')),
                                  ),
                                  ButtonSegment<String>(
                                    value: 'client',
                                    icon: const Icon(Icons.travel_explore_outlined),
                                    label: Text(_tr(ru: 'Клиент', uz: 'Mijoz')),
                                  ),
                                ],
                                selected: {_entryMode},
                                onSelectionChanged: (v) {
                                  if (v.isEmpty) return;
                                  setState(() {
                                    _entryMode = v.first;
                                    _error = null;
                                    _clientError = null;
                                    if (_entryMode == 'client') {
                                      _resetClientFlow();
                                    }
                                  });
                                  if (_entryMode == 'client') {
                                    _maybeOpenClientPin();
                                  }
                                },
                              ),
                              const SizedBox(height: 18),
                              if (_entryMode == 'staff') ...[
                                TextFormField(
                                  controller: _usernameController,
                                  decoration: InputDecoration(
                                    labelText: _tr(
                                      ru: 'Имя пользователя',
                                      uz: 'Foydalanuvchi nomi',
                                    ),
                                    prefixIcon: const Icon(Icons.person_outline_rounded),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                  ),
                                  validator: (v) => (v == null || v.trim().isEmpty)
                                      ? _tr(
                                          ru: 'Введите имя пользователя',
                                          uz: 'Foydalanuvchi nomini kiriting',
                                        )
                                      : null,
                                ),
                                const SizedBox(height: 12),
                                TextFormField(
                                  controller: _passwordController,
                                  obscureText: true,
                                  decoration: InputDecoration(
                                    labelText: _tr(ru: 'Пароль', uz: 'Parol'),
                                    prefixIcon: const Icon(Icons.lock_outline_rounded),
                                    border: OutlineInputBorder(
                                      borderRadius: BorderRadius.circular(14),
                                    ),
                                  ),
                                  validator: (v) => (v == null || v.isEmpty)
                                      ? _tr(ru: 'Введите пароль', uz: 'Parolni kiriting')
                                      : null,
                                ),
                                const SizedBox(height: 12),
                                if (_error != null)
                                  Text(
                                    _error!,
                                    style: const TextStyle(color: Color(0xFFDC2626), fontWeight: FontWeight.w600),
                                    textAlign: TextAlign.center,
                                  ),
                                const SizedBox(height: 8),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton(
                                    style: FilledButton.styleFrom(
                                      backgroundColor: const Color(0xFF1D4ED8),
                                      foregroundColor: Colors.white,
                                      minimumSize: const Size.fromHeight(50),
                                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                    onPressed: _loading ? null : _login,
                                    child: _loading
                                        ? const SizedBox(
                                            height: 18,
                                            width: 18,
                                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                          )
                                        : Text(_tr(ru: 'Войти', uz: 'Kirish')),
                                  ),
                                ),
                              ] else ...[
                                Container(
                                  width: double.infinity,
                                  padding: const EdgeInsets.all(12),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFF8FAFC),
                                    borderRadius: BorderRadius.circular(12),
                                    border: Border.all(color: const Color(0xFFE2E8F0)),
                                  ),
                                  child: Text(
                                    _tr(
                                      ru: 'Режим клиента: подтвердите email кодом и продолжайте.',
                                      uz: 'Mijoz rejimi: email kodini tasdiqlang va davom eting.',
                                    ),
                                    style: const TextStyle(height: 1.3, color: Color(0xFF334155)),
                                  ),
                                ),
                                const SizedBox(height: 10),
                                TextField(
                                  controller: _clientEmailController,
                                  keyboardType: TextInputType.emailAddress,
                                  decoration: InputDecoration(
                                    labelText: _tr(ru: 'Email', uz: 'Email'),
                                    prefixIcon: const Icon(Icons.email_outlined),
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                SizedBox(
                                  width: double.infinity,
                                  child: FilledButton(
                                    onPressed: _clientBusy ? null : _clientSendCode,
                                    child: _clientBusy
                                        ? const SizedBox(
                                            height: 18,
                                            width: 18,
                                            child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                          )
                                        : Text(_tr(ru: 'Отправить код', uz: 'Kodni yuborish')),
                                  ),
                                ),
                                if (_clientStep >= 1) ...[
                                  const SizedBox(height: 12),
                                  TextField(
                                    controller: _clientCodeController,
                                    keyboardType: TextInputType.number,
                                    decoration: InputDecoration(
                                      labelText: _tr(ru: 'Код подтверждения', uz: 'Tasdiqlash kodi'),
                                      prefixIcon: const Icon(Icons.verified_outlined),
                                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  SizedBox(
                                    width: double.infinity,
                                    child: FilledButton(
                                      onPressed: _clientBusy ? null : _clientVerifyCode,
                                      child: _clientBusy
                                          ? const SizedBox(
                                              height: 18,
                                              width: 18,
                                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                            )
                                          : Text(_tr(ru: 'Подтвердить код', uz: 'Kodni tasdiqlash')),
                                    ),
                                  ),
                                ],
                                if (_clientStep >= 2) ...[
                                  const SizedBox(height: 12),
                                  TextField(
                                    controller: _clientPasswordController,
                                    obscureText: true,
                                    decoration: InputDecoration(
                                      labelText: _tr(ru: 'Пароль', uz: 'Parol'),
                                      prefixIcon: const Icon(Icons.lock_outline_rounded),
                                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                                    ),
                                  ),
                                  const SizedBox(height: 8),
                                  SizedBox(
                                    width: double.infinity,
                                    child: FilledButton(
                                      onPressed: _clientBusy ? null : _clientAuth,
                                      child: _clientBusy
                                          ? const SizedBox(
                                              height: 18,
                                              width: 18,
                                              child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                            )
                                          : Text(_clientExists
                                              ? _tr(ru: 'Войти', uz: 'Kirish')
                                              : _tr(ru: 'Создать аккаунт', uz: 'Akkaunt yaratish')),
                                    ),
                                  ),
                                ],
                                if (_clientError != null) ...[
                                  const SizedBox(height: 8),
                                  Text(
                                    _clientError!,
                                    style: const TextStyle(color: Color(0xFFDC2626), fontWeight: FontWeight.w600),
                                    textAlign: TextAlign.center,
                                  ),
                                ],
                              ],
                            ],
                          ),
                          Positioned(
                            right: 2,
                            top: 2,
                            child: Builder(
                              builder: (iconContext) => IconButton(
                                onPressed: () => _openLoginLangMenu(iconContext),
                                icon: Image.asset('assets/icons/language.png', width: 20, height: 20),
                                tooltip: _uiLang == 'ru' ? 'RU' : 'UZ',
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          if (_loading || _checkingSession)
            Positioned.fill(
              child: Container(
                color: Colors.black.withOpacity(0.18),
                child: const Center(child: CircularProgressIndicator()),
              ),
            ),
        ],
      ),
    );
  }
}

class ClientCatalogWebViewScreen extends StatefulWidget {
  const ClientCatalogWebViewScreen({super.key, required this.lang});

  final String lang;

  @override
  State<ClientCatalogWebViewScreen> createState() => _ClientCatalogWebViewScreenState();
}

class _ClientCatalogWebViewScreenState extends State<ClientCatalogWebViewScreen> {
  late final WebViewController _controller;
  final WebViewCookieManager _cookieManager = WebViewCookieManager();
  bool _loading = true;
  String _currentUrl = '';
  bool _handlingInvalidToken = false;

  String _t({
    required String ru,
    required String uz,
  }) {
    return widget.lang == 'ru' ? ru : uz;
  }

  Future<void> _goToCatalogPath(String path) async {
    final clean = path.startsWith('/') ? path : '/$path';
    await _controller.loadRequest(Uri.parse('https://hmsuz.com$clean?lang=${widget.lang}'));
  }

  Future<void> _logoutPublicUser() async {
    await _controller.loadRequest(Uri.parse('https://hmsuz.com/logout'));
    await Future<void>.delayed(const Duration(milliseconds: 300));
    await _goToCatalogPath('/catalog');
  }

  Future<void> _handleInvalidToken() async {
    if (_handlingInvalidToken) return;
    _handlingInvalidToken = true;
    try {
      await _cookieManager.clearCookies();
      await _controller.clearCache();
      await _controller.runJavaScript('localStorage.clear(); sessionStorage.clear();');
    } catch (_) {}
    if (mounted) {
      await _controller.loadRequest(Uri.parse('https://hmsuz.com/login?lang=${widget.lang}'));
    }
  }

  @override
  void initState() {
    super.initState();
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            if (!mounted) return;
            setState(() => _loading = true);
          },
          onPageFinished: (_) {
            if (!mounted) return;
            _controller.currentUrl().then((v) {
              if (!mounted) return;
              setState(() => _currentUrl = v ?? '');
            });
            setState(() => _loading = false);
            _controller
                .runJavaScriptReturningResult("document.body && document.body.innerText")
                .then((value) {
              if (!mounted) return;
              final raw = value?.toString() ?? '';
              final text = raw.replaceAll('"', '').toLowerCase();
              if (text.contains('invalid token')) {
                _handleInvalidToken();
              }
            }).catchError((_) {});
          },
        ),
      )
      ..loadRequest(Uri.parse('https://hmsuz.com/auth/google/start?lang=${widget.lang}'));
  }

  @override
  Widget build(BuildContext context) {
    final ru = widget.lang == 'ru';
    return Scaffold(
      appBar: AppBar(
        title: Text(ru ? 'Клиент' : 'Mijoz'),
        actions: [
          IconButton(
            tooltip: _t(ru: 'Каталог', uz: 'Katalog'),
            onPressed: () => _goToCatalogPath('/catalog'),
            icon: const Icon(Icons.home_outlined),
          ),
          PopupMenuButton<String>(
            tooltip: _t(ru: 'Профиль', uz: 'Profil'),
            onSelected: (value) {
              switch (value) {
                case 'bookings':
                  _goToCatalogPath('/catalog/booking-history');
                  break;
                case 'feedbacks':
                  _goToCatalogPath('/catalog/feedbacks');
                  break;
                case 'account':
                  _goToCatalogPath('/catalog/my-account');
                  break;
                case 'settings':
                  _goToCatalogPath('/catalog/settings');
                  break;
                case 'logout':
                  _logoutPublicUser();
                  break;
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'bookings',
                child: Text(_t(ru: 'Мои брони', uz: 'Mening bronlarim')),
              ),
              PopupMenuItem(
                value: 'feedbacks',
                child: Text(_t(ru: 'Мои отзывы', uz: 'Fikrlarim')),
              ),
              PopupMenuItem(
                value: 'account',
                child: Text(_t(ru: 'Мой аккаунт', uz: 'Mening akkauntim')),
              ),
              PopupMenuItem(
                value: 'settings',
                child: Text(_t(ru: 'Настройки', uz: 'Sozlamalar')),
              ),
              PopupMenuItem(
                value: 'logout',
                child: Text(_t(ru: 'Выйти', uz: 'Chiqish')),
              ),
            ],
            icon: const Icon(Icons.account_circle_outlined),
          ),
        ],
      ),
      body: Stack(
        children: [
          WebViewWidget(controller: _controller),
          if (_currentUrl.isNotEmpty)
            Positioned(
              right: 10,
              bottom: 10,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  color: Colors.black.withOpacity(0.55),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  child: Text(
                    _currentUrl.replaceFirst('https://hmsuz.com', ''),
                    style: const TextStyle(color: Colors.white, fontSize: 11),
                  ),
                ),
              ),
            ),
          if (_loading)
            const Positioned.fill(
              child: ColoredBox(
                color: Color(0x22000000),
                child: Center(child: CircularProgressIndicator()),
              ),
            ),
        ],
      ),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key, required this.accessToken, required this.branchId});

  final String accessToken;
  final int branchId;

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> with WidgetsBindingObserver {
  int _index = 0;
  late final _api = _ApiClient(widget.accessToken, widget.branchId);
  final ValueNotifier<int> _refreshSignal = ValueNotifier<int>(0);
  String _language = 'ru';
  bool _changingLang = false;
  int _unreadCount = 0;
  StreamSubscription<String>? _fcmTokenRefreshSub;
  StreamSubscription<RemoteMessage>? _fcmForegroundSub;
  Timer? _unreadPollTimer;
  bool _firebaseReady = false;

  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: _language);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _loadTopLanguage();
    _loadUnreadCount();
    _initPushNotifications();
    _unreadPollTimer = Timer.periodic(const Duration(seconds: 25), (_) {
      _loadUnreadCount();
    });
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _fcmTokenRefreshSub?.cancel();
    _fcmForegroundSub?.cancel();
    _unreadPollTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _loadUnreadCount();
    }
  }

  void _notifyDataChanged() {
    _refreshSignal.value = _refreshSignal.value + 1;
  }

  Future<void> _loadTopLanguage() async {
    try {
      final me = await _api.getJson('/auth/me');
      if (!mounted) return;
      final lang = normLang('${(me as Map)['language'] ?? 'uz'}');
      setState(() => _language = lang);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kLanguageKey, _language);
      appLang.value = _language;
    } catch (_) {
      final prefs = await SharedPreferences.getInstance();
      final lang = normLang(prefs.getString(kLanguageKey));
      if (!mounted) return;
      setState(() => _language = lang);
      appLang.value = lang;
    }
  }

  Future<void> _setTopLanguage(String lang) async {
    lang = normLang(lang);
    if (_changingLang || _language == lang) return;
    setState(() => _changingLang = true);
    try {
      await _api.postJson('/settings/language', {'language': lang});
      if (!mounted) return;
      setState(() => _language = lang);
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kLanguageKey, lang);
      appLang.value = lang;
      showAppAlert(context, lang == 'ru' ? 'Язык: Русский' : "Til: O'zbekcha");
    } catch (e) {
      if (!mounted) return;
      showAppAlert(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => _changingLang = false);
    }
  }

  Future<void> _loadUnreadCount() async {
    try {
      final data = await _api.getJson('/users/me/notifications', query: const {
        'limit': '1',
        'offset': '0',
      });
      final count = (data is Map && data['unread_count'] is num)
          ? (data['unread_count'] as num).toInt()
          : 0;
      if (!mounted) return;
      setState(() => _unreadCount = count);
    } catch (_) {}
  }

  Future<void> _initPushNotifications() async {
    try {
      await Firebase.initializeApp();
      _firebaseReady = true;
    } catch (_) {
      _firebaseReady = false;
      return;
    }

    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();

      final token = await messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _registerDeviceToken(token);
      }

      _fcmTokenRefreshSub = messaging.onTokenRefresh.listen((newToken) async {
        await _registerDeviceToken(newToken);
      });

      _fcmForegroundSub = FirebaseMessaging.onMessage.listen((event) async {
        await _loadUnreadCount();
        if (!mounted) return;
        final title = event.notification?.title ?? _t('Уведомление', 'Bildirishnoma');
        final body = event.notification?.body ?? _t('Новое сообщение', 'Yangi xabar');
        showAppAlert(context, '$title\n$body');
      });
    } catch (_) {}
  }

  Future<void> _registerDeviceToken(String token) async {
    try {
      await _api.postJson('/users/me/device-token', {
        'fcm_token': token,
        'platform': 'android',
      });
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('fcm_token', token);
    } catch (_) {}
  }

  Future<void> _openNotifications() async {
    await Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => _NotificationsPage(api: _api, language: _language)),
    );
    await _loadUnreadCount();
  }

  Future<void> _logout() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedToken = prefs.getString('fcm_token');
      if (savedToken != null && savedToken.isNotEmpty) {
        await _api.deleteJson('/users/me/device-token', body: {'fcm_token': savedToken});
      } else if (_firebaseReady) {
        final t = await FirebaseMessaging.instance.getToken();
        if (t != null && t.isNotEmpty) {
          await _api.deleteJson('/users/me/device-token', body: {'fcm_token': t});
        } else {
          await _api.deleteJson('/users/me/device-token');
        }
      }
    } catch (_) {}

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('access_token');
    await prefs.remove('branch_id');
    await prefs.remove('user_id');
    await prefs.remove('is_admin');
    await prefs.remove('fcm_token');
    if (!mounted) return;
    Navigator.of(context).pushAndRemoveUntil(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
      (route) => false,
    );
  }

  @override
  Widget build(BuildContext context) {
    final lang = appLang.value;
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: const Text(
          'HMS',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 20),
        ),
        actions: [
          PopupMenuButton<String>(
            tooltip: 'Change language',
            enabled: !_changingLang,
            onSelected: _setTopLanguage,
            itemBuilder: (_) => [
              CheckedPopupMenuItem<String>(
                value: 'ru',
                checked: _language == 'ru',
                child: const Text('Русский'),
              ),
              CheckedPopupMenuItem<String>(
                value: 'uz',
                checked: _language == 'uz',
                child: const Text("O'zbekcha"),
              ),
            ],
            icon: Image.asset(
              'assets/icons/language.png',
              width: 20,
              height: 20,
            ),
          ),
          IconButton(
            tooltip: _language == 'ru' ? 'Уведомления' : 'Bildirishnomalar',
            onPressed: _openNotifications,
            icon: Stack(
              clipBehavior: Clip.none,
              children: [
                const Icon(Icons.notifications_outlined, size: 24),
                if (_unreadCount > 0)
                  Positioned(
                    right: -6,
                    top: -6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                        color: const Color(0xFFDC2626),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      constraints: const BoxConstraints(minWidth: 16, minHeight: 16),
                      child: Text(
                        _unreadCount > 99 ? '99+' : '$_unreadCount',
                        textAlign: TextAlign.center,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 10,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          IconButton(
            tooltip: 'Logout',
            onPressed: _logout,
            icon: Image.asset(
              'assets/icons/logout.png',
              width: 20,
              height: 20,
            ),
          ),
        ],
      ),
      body: IndexedStack(
        index: _index,
        children: [
          _DashboardPage(api: _api, refreshSignal: _refreshSignal),
          _RoomsPage(api: _api, onDataChanged: _notifyDataChanged),
          _BookingsPage(api: _api, onDataChanged: _notifyDataChanged),
          _PaymentsPage(api: _api),
          _SettingsPage(api: _api),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        height: 76,
        backgroundColor: Colors.white,
        indicatorColor: const Color(0xFFDDF3F1),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        selectedIndex: _index,
        onDestinationSelected: (i) {
          setState(() => _index = i);
          if (i == 0) {
            _notifyDataChanged();
          }
        },
        destinations: [
          NavigationDestination(
            icon: const _WebIcon('home_menu', size: 22),
            label: trPair(ru: 'Главная', uz: 'Dashboard', lang: lang),
          ),
          NavigationDestination(
            icon: const _WebIcon('rooms_menu', size: 22),
            label: trPair(ru: 'Комнаты', uz: 'Honalar', lang: lang),
          ),
          NavigationDestination(
            icon: const _WebIcon('booking_menu', size: 22),
            label: trPair(ru: 'Бронь', uz: 'Buyurtmalar', lang: lang),
          ),
          NavigationDestination(
            icon: const _WebIcon('payments_menu', size: 22),
            label: trPair(ru: 'Платежи', uz: "To'lovlar", lang: lang),
          ),
          NavigationDestination(
            icon: const _WebIcon('settings_menu', size: 22),
            label: trPair(ru: 'Настройки', uz: 'Sozlash', lang: lang),
          ),
        ],
      ),
    );
  }
}

class _ApiClient {
  _ApiClient(this.token, this.branchId);

  static const String baseApi = 'https://hmsuz.com/api';
  static const Duration timeout = Duration(seconds: 18);

  final String token;
  final int branchId;

  bool _isTransientNetworkError(Object e) {
    return e is TimeoutException || e is SocketException || e is http.ClientException;
  }

  Future<http.Response> _runWithRetry(Future<http.Response> Function() request) async {
    try {
      return await request().timeout(timeout);
    } catch (e) {
      if (!_isTransientNetworkError(e)) rethrow;
      await Future.delayed(const Duration(milliseconds: 900));
      return await request().timeout(timeout);
    }
  }

  Future<dynamic> getJson(String path, {Map<String, String>? query}) async {
    final uri = Uri.parse('$baseApi$path').replace(queryParameters: query);
    final r = await _runWithRetry(() => http.get(
          uri,
          headers: {'Authorization': 'Bearer $token'},
        ));
    if (r.statusCode != 200) throw Exception('status ${r.statusCode}: ${r.body}');
    return jsonDecode(r.body);
  }

  Future<dynamic> postJson(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseApi$path');
    final r = await _runWithRetry(() => http.post(
          uri,
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        ));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw Exception('status ${r.statusCode}: ${r.body}');
    }
    return r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
  }

  Future<dynamic> putJson(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$baseApi$path');
    final r = await _runWithRetry(() => http.put(
          uri,
          headers: {
            'Authorization': 'Bearer $token',
            'Content-Type': 'application/json',
          },
          body: jsonEncode(body),
        ));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw Exception('status ${r.statusCode}: ${r.body}');
    }
    return r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
  }

  Future<dynamic> deleteJson(
    String path, {
    Map<String, String>? query,
    Map<String, dynamic>? body,
  }) async {
    final uri = Uri.parse('$baseApi$path').replace(queryParameters: query);
    final r = await _runWithRetry(() => http.delete(
          uri,
          headers: {
            'Authorization': 'Bearer $token',
            if (body != null) 'Content-Type': 'application/json',
          },
          body: body != null ? jsonEncode(body) : null,
        ));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw Exception('status ${r.statusCode}: ${r.body}');
    }
    return r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
  }

  Future<dynamic> putQuery(String path, Map<String, String> query) async {
    final uri = Uri.parse('$baseApi$path').replace(queryParameters: query);
    final r = await _runWithRetry(() => http.put(
          uri,
          headers: {'Authorization': 'Bearer $token'},
        ));
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw Exception('status ${r.statusCode}: ${r.body}');
    }
    return r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
  }

  Future<dynamic> postMultipart(
    String path, {
    Map<String, String>? query,
    List<http.MultipartFile>? files,
    Map<String, String>? fields,
  }) async {
    final uri = Uri.parse('$baseApi$path').replace(queryParameters: query);
    final req = http.MultipartRequest('POST', uri);
    req.headers['Authorization'] = 'Bearer $token';
    if (fields != null && fields.isNotEmpty) {
      req.fields.addAll(fields);
    }
    if (files != null && files.isNotEmpty) {
      req.files.addAll(files);
    }
    final stream = await req.send().timeout(timeout);
    final r = await http.Response.fromStream(stream);
    if (r.statusCode < 200 || r.statusCode >= 300) {
      throw Exception('status ${r.statusCode}: ${r.body}');
    }
    return r.body.isEmpty ? <String, dynamic>{} : jsonDecode(r.body);
  }

  Future<List<Map<String, dynamic>>> listRoomImages(int roomId) async {
    final data = await getJson('/rooms/$roomId/images', query: {
      'branch_id': branchId.toString(),
    }) as Map;
    final rows = (data['images'] as List?) ?? const [];
    return rows.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<void> uploadRoomImage(
    int roomId, {
    required String filePath,
    bool isCover = false,
  }) async {
    final file = await http.MultipartFile.fromPath('files', filePath);
    await postMultipart(
      '/rooms/$roomId/images',
      query: {
        'branch_id': branchId.toString(),
        'is_cover': isCover ? 'true' : 'false',
      },
      files: [file],
    );
  }

  Future<List<Map<String, dynamic>>> listBranchImages(int branchId) async {
    final data = await getJson('/branches/admin/$branchId/images') as Map;
    final rows = (data['images'] as List?) ?? const [];
    return rows.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
  }

  Future<void> uploadBranchImage(
    int branchId, {
    required String filePath,
    bool isCover = false,
  }) async {
    final file = await http.MultipartFile.fromPath('files', filePath);
    await postMultipart(
      '/branches/admin/$branchId/images',
      fields: {
        'is_cover': isCover ? 'true' : 'false',
      },
      files: [file],
    );
  }

  Future<void> setBranchImageCover(int branchId, int imageId) async {
    await putQuery('/branches/admin/$branchId/images/$imageId/cover', {});
  }

  Future<void> deleteBranchImage(int branchId, int imageId) async {
    await deleteJson('/branches/admin/$branchId/images/$imageId');
  }

  Future<void> setRoomImageCover(int roomId, int imageId) async {
    await putQuery('/rooms/$roomId/images/$imageId/cover', {
      'branch_id': branchId.toString(),
    });
  }

  Future<void> deleteRoomImage(int roomId, int imageId) async {
    await deleteJson('/rooms/$roomId/images/$imageId', query: {
      'branch_id': branchId.toString(),
    });
  }
}

class _DashboardPage extends StatefulWidget {
  const _DashboardPage({required this.api, required this.refreshSignal});
  final _ApiClient api;
  final ValueNotifier<int> refreshSignal;

  @override
  State<_DashboardPage> createState() => _DashboardPageState();
}

class _DashboardPageState extends State<_DashboardPage> {
  DateTime _fromDate = DateTime.now();
  DateTime _toDate = DateTime.now();
  DateTime? _appliedFromDate;
  DateTime? _appliedToDate;
  late Future<dynamic> _dashboardFuture;
  final Map<int, int> _futureByBed = {};
  Timer? _ticker;
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz);

  @override
  void initState() {
    super.initState();
    widget.refreshSignal.addListener(_onExternalRefresh);
    _reloadDashboard();
    _ticker = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void didUpdateWidget(covariant _DashboardPage oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshSignal != widget.refreshSignal) {
      oldWidget.refreshSignal.removeListener(_onExternalRefresh);
      widget.refreshSignal.addListener(_onExternalRefresh);
    }
  }

  @override
  void dispose() {
    widget.refreshSignal.removeListener(_onExternalRefresh);
    _ticker?.cancel();
    super.dispose();
  }

  void _onExternalRefresh() {
    if (!mounted) return;
    setState(() {
      _reloadDashboard();
    });
  }

  Future<void> _pickDate(bool isFrom) async {
    final initial = isFrom ? _fromDate : _toDate;
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (picked == null) return;
    setState(() {
      if (isFrom) {
        _fromDate = picked;
      } else {
        _toDate = picked;
      }
    });
  }

  String _fmt(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(d.month)}/${two(d.day)}/${d.year}';
  }

  String _apiDate(DateTime d) {
    String two(int n) => n.toString().padLeft(2, '0');
    return '${d.year}-${two(d.month)}-${two(d.day)}';
  }

  DateTime? _parseDateFlex(String? raw) {
    if (raw == null) return null;
    final s = raw.trim();
    if (s.isEmpty) return null;

    final iso = DateTime.tryParse(s);
    if (iso != null) return iso;

    final noTime = s.split(' ').first;
    final parts = noTime.split('/');
    if (parts.length == 3) {
      final a = int.tryParse(parts[0]);
      final b = int.tryParse(parts[1]);
      final c = int.tryParse(parts[2]);
      if (a != null && b != null && c != null) {
        if (parts[0].length == 4) {
          // yyyy/mm/dd
          return DateTime(a, b, c);
        }
        // mm/dd/yyyy (web-style in your screenshots)
        return DateTime(c, a, b);
      }
    }
    return null;
  }

  String _formatShortDate(String? value) {
    if (value == null || value.isEmpty) return '';
    final dt = _parseDateFlex(value);
    if (dt == null) return value;
    String two(int n) => n.toString().padLeft(2, '0');
    return '${two(dt.month)}/${two(dt.day)}/${dt.year}';
  }

  void _applyFilter() {
    if (_fromDate.isAfter(_toDate)) {
      showAppAlert(context, _t('Дата "С" должна быть раньше даты "По"', "Boshlanish sanasi tugashdan oldin bo'lishi kerak"), error: true);
      return;
    }
    setState(() {
      _appliedFromDate = _fromDate;
      _appliedToDate = _toDate;
    });
    _reloadDashboard();
  }

  void _clearFilter() {
    setState(() {
      _appliedFromDate = null;
      _appliedToDate = null;
      _fromDate = DateTime.now();
      _toDate = DateTime.now();
    });
    _reloadDashboard();
  }

  Map<String, String> _currentQuery() {
    final query = <String, String>{
      'branch_id': widget.api.branchId.toString(),
    };
    if (_appliedFromDate != null && _appliedToDate != null) {
      query['checkin_date'] = _apiDate(_appliedFromDate!);
      query['checkout_date'] = _apiDate(_appliedToDate!);
    }
    return query;
  }

  void _reloadDashboard() {
    _dashboardFuture = widget.api.getJson('/dashboard/rooms', query: _currentQuery());
    _refreshFutureIndex();
  }

  Future<void> _refreshFutureIndex() async {
    final endpoints = <String>['/future-bookings/', '/future-bookings/list', '/bookings/future'];
    for (final ep in endpoints) {
      try {
        final data = await widget.api.getJson(ep, query: {'branch_id': widget.api.branchId.toString()});
        dynamic payload = data;
        if (data is Map<String, dynamic>) {
          payload = data['items'] ?? data['data'] ?? const [];
        }
        if (payload is List) {
          final next = <int, int>{};
          for (final item in payload.whereType<Map>()) {
            final m = Map<String, dynamic>.from(item);
            final bedId = _asInt(m['bed_id'] ?? m['bedId']);
            if (bedId != null) {
              next[bedId] = (next[bedId] ?? 0) + 1;
            }
          }
          if (!mounted) return;
          setState(() {
            _futureByBed
              ..clear()
              ..addAll(next);
          });
          return;
        }
      } catch (_) {}
    }

    // Fallback: derive future bookings from active bookings list
    // (some backends expose future rows here, like web logic).
    try {
      final data = await widget.api.getJson('/active-bookings/', query: {
        'branch_id': widget.api.branchId.toString(),
      });
      if (data is List) {
        final now = DateTime.now();
        final next = <int, int>{};
        for (final item in data.whereType<Map>()) {
          final m = Map<String, dynamic>.from(item);
          final bedId = _asInt(m['bed_id'] ?? m['bedId']);
          final checkin = _parseDateFlex('${m['checkin_date'] ?? ''}');
          if (bedId != null && checkin != null && checkin.isAfter(now)) {
            next[bedId] = (next[bedId] ?? 0) + 1;
          }
        }
        if (!mounted) return;
        setState(() {
          _futureByBed
            ..clear()
            ..addAll(next);
        });
      }
    } catch (_) {}
  }

  Future<void> _pullRefresh() async {
    setState(() {
      _reloadDashboard();
    });
    await _dashboardFuture;
  }

  bool get _hasActiveFilter => _appliedFromDate != null && _appliedToDate != null;

  Map<String, String> _timeLeft(String? targetDate, {bool dateOnlyAsEndOfDay = true}) {
    if (targetDate == null || targetDate.isEmpty) {
      return {'d': '00', 'h': '00', 'm': '00', 's': '00'};
    }
    DateTime? parsed = _parseDateFlex(targetDate);
    if (parsed != null && !targetDate.contains('T') && dateOnlyAsEndOfDay) {
      parsed = DateTime(parsed.year, parsed.month, parsed.day, 23, 59, 59);
    }
    if (parsed == null) return {'d': '00', 'h': '00', 'm': '00', 's': '00'};
    final diff = parsed.difference(DateTime.now());
    if (diff.isNegative) return {'d': '00', 'h': '00', 'm': '00', 's': '00'};
    final d = diff.inDays;
    final h = diff.inHours.remainder(24);
    final m = diff.inMinutes.remainder(60);
    final s = diff.inSeconds.remainder(60);
    String two(int n) => n.toString().padLeft(2, '0');
    return {'d': two(d), 'h': two(h), 'm': two(m), 's': two(s)};
  }

  String _bedTypeEmoji(String t) {
    switch (t) {
      case 'double':
        return '👥';
      case 'child':
        return '🧸';
      default:
        return '👤';
    }
  }

  int? _asInt(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse('${v ?? ''}');
  }

  List<Map<String, dynamic>> _extractFutureBookings(Map<String, dynamic> bed) {
    final dynamic raw = bed['future_bookings'] ??
        bed['upcoming_bookings'] ??
        bed['futureBookings'] ??
        bed['next_bookings'] ??
        bed['future_booking'] ??
        bed['future_reservations'] ??
        bed['next_booking'] ??
        bed['upcoming_booking'];
    if (raw is List) {
      return raw.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
    }
    if (raw is Map) return [Map<String, dynamic>.from(raw)];
    return const [];
  }

  bool _hasFutureHint(Map<String, dynamic> bed, List<Map<String, dynamic>> rows) {
    if (rows.isNotEmpty) return true;
    if (bed['has_future'] == true) return true;
    final flags = [
      bed['has_future_booking'],
      bed['has_future_bookings'],
      bed['future_booking_exists'],
    ];
    if (flags.any((f) => f == true)) return true;
    final counts = [
      _asInt(bed['future_booking_count']) ?? 0,
      _asInt(bed['future_bookings_count']) ?? 0,
      _asInt(bed['upcoming_count']) ?? 0,
    ];
    if (counts.any((c) => c > 0)) return true;
    final now = DateTime.now();
    for (final entry in bed.entries) {
      final k = entry.key.toLowerCase();
      final v = entry.value;
      final looksFuture = k.contains('future') || k.contains('upcoming') || k.contains('next');
      if (!looksFuture) continue;
      if (v == null) continue;
      if (v is bool && v) return true;
      if (v is num && v > 0) return true;
      if (v is String && v.trim().isNotEmpty) {
        final parsed = _parseDateFlex(v.trim());
        if (parsed == null || parsed.isAfter(now)) return true;
      }
      if (v is List && v.isNotEmpty) return true;
      if (v is Map && v.isNotEmpty) return true;
    }
    return _futureCheckinDate(bed).isNotEmpty;
  }

  String _futureCheckinDate(Map<String, dynamic> bed) {
    final fromList = _extractFutureBookings(bed);
    if (fromList.isNotEmpty) {
      final v = '${fromList.first['checkin_date'] ?? ''}';
      if (v.isNotEmpty) return v;
    }
    final direct = '${bed['next_checkin_date'] ?? bed['future_checkin_date'] ?? bed['next_checkin'] ?? ''}';
    return direct;
  }

  Future<List<Map<String, dynamic>>> _loadFutureBookings(int roomId, int bedId, List<Map<String, dynamic>> seed) async {
    if (seed.isNotEmpty) return seed;
    final attempts = <Map<String, dynamic>>[
      {
        'path': '/dashboard/beds/future-bookings',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/future-bookings/',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'room_id': roomId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/future-bookings/list',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'room_id': roomId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/bookings/future',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'room_id': roomId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/future-bookings/',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/bookings/future',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'bed_id': bedId.toString(),
        }
      },
      {
        'path': '/active-bookings/',
        'query': {
          'branch_id': widget.api.branchId.toString(),
          'bed_id': bedId.toString(),
          'future': '1',
        }
      },
      {
        'path': '/active-bookings/',
        'query': {
          'branch_id': widget.api.branchId.toString(),
        }
      },
    ];

    for (final a in attempts) {
      try {
        final data = await widget.api.getJson(a['path'] as String, query: a['query'] as Map<String, String>);
        dynamic payload = data;
        if (data is Map<String, dynamic>) {
          payload = data['items'] ?? data['data'] ?? const [];
        }
        if (payload is List) {
          final rows = payload.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
          final filtered = rows.where((m) {
            final bid = _asInt(m['bed_id'] ?? m['bedId'] ?? m['id']);
            final rid = _asInt(m['room_id'] ?? m['roomId']);
            final byBed = bid == null || bid == bedId;
            final byRoom = rid == null || rid == roomId;
            final checkin = _parseDateFlex('${m['checkin_date'] ?? ''}');
            final futureOnly = checkin == null || checkin.isAfter(DateTime.now());
            return byBed && byRoom && futureOnly;
          }).toList();
          if (filtered.isNotEmpty) return filtered;
          if (rows.isNotEmpty) return rows;
        }
      } catch (_) {
        // try next endpoint
      }
    }

    // Strong fallback: booking history usually contains future rows too.
    try {
      final now = DateTime.now();
      final from = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      final toDt = now.add(const Duration(days: 365));
      final to = '${toDt.year}-${toDt.month.toString().padLeft(2, '0')}-${toDt.day.toString().padLeft(2, '0')}';
      final data = await widget.api.getJson('/booking-history/', query: {
        'branch_id': widget.api.branchId.toString(),
        'from_date': from,
        'to_date': to,
      });
      if (data is List) {
        final rows = data.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
        final filtered = rows.where((m) {
          final bid = _asInt(m['bed_id'] ?? m['bedId']);
          final rid = _asInt(m['room_id'] ?? m['roomId']);
          final checkin = _parseDateFlex('${m['checkin_date'] ?? ''}');
          return (bid == null || bid == bedId) &&
              (rid == null || rid == roomId) &&
              (checkin == null || checkin.isAfter(now));
        }).toList();
        if (filtered.isNotEmpty) return filtered;
      }
    } catch (_) {}

    return const [];
  }

  Future<void> _cancelFutureBooking(Map<String, dynamic> booking) async {
    final endpoints = <String>[
      '/future-bookings/cancel',
      '/bookings/future/cancel',
      '/active-bookings/cancel',
    ];
    Exception? lastError;
    for (final ep in endpoints) {
      try {
        await widget.api.postJson(ep, {
          'booking_id': booking['id'],
          'branch_id': widget.api.branchId,
        });
        return;
      } catch (e) {
        lastError = Exception('$e');
      }
    }
    if (lastError != null) throw lastError;
  }

  Future<void> _updateFutureBooking({
    required Map<String, dynamic> booking,
    required int roomId,
    required int bedId,
    required String checkinDate,
    required String checkoutDate,
    required double totalAmount,
  }) async {
    final endpoints = <String>[
      '/future-bookings/update-admin',
      '/bookings/future/update-admin',
      '/active-bookings/update-admin',
    ];
    Exception? lastError;
    for (final ep in endpoints) {
      try {
        await widget.api.postJson(ep, {
          'booking_id': booking['id'],
          'room_id': roomId,
          'bed_id': bedId,
          'checkin_date': checkinDate,
          'checkout_date': checkoutDate,
          'total_amount': totalAmount,
        });
        return;
      } catch (e) {
        lastError = Exception('$e');
      }
    }
    if (lastError != null) throw lastError;
  }

  Future<void> _openEditFutureBooking(Map<String, dynamic> booking) async {
    int roomId = (booking['room_id'] as num?)?.toInt() ?? 0;
    int bedId = (booking['bed_id'] as num?)?.toInt() ?? 0;
    DateTime checkin = DateTime.tryParse('${booking['checkin_date'] ?? ''}') ?? DateTime.now();
    DateTime checkout = DateTime.tryParse('${booking['checkout_date'] ?? ''}') ?? DateTime.now().add(const Duration(days: 1));
    final totalCtrl = TextEditingController(text: '${booking['total_amount'] ?? 0}');
    List<dynamic> rooms = [];
    List<dynamic> beds = [];

    Future<void> loadRooms() async {
      rooms = (await widget.api.getJson('/rooms/', query: {
        'branch_id': widget.api.branchId.toString(),
      }) as List)
          .cast<dynamic>();
      if (roomId == 0 && rooms.isNotEmpty) roomId = (rooms.first['id'] as num).toInt();
    }

    Future<void> loadBeds() async {
      if (roomId == 0) {
        beds = [];
        return;
      }
      beds = (await widget.api.getJson('/beds/', query: {
        'branch_id': widget.api.branchId.toString(),
        'room_id': roomId.toString(),
      }) as List)
          .cast<dynamic>();
      if (!beds.any((b) => (b['id'] as num).toInt() == bedId) && beds.isNotEmpty) {
        bedId = (beds.first['id'] as num).toInt();
      }
    }

    await loadRooms();
    await loadBeds();
    if (!mounted) return;

    String fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          title: Text(_t('Редактировать будущее бронирование', 'Kelgusi bronni tahrirlash')),
          content: SingleChildScrollView(
            child: SizedBox(
              width: 360,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<int>(
                    value: roomId == 0 ? null : roomId,
                    decoration: InputDecoration(labelText: _t('Комната', 'Xona'), border: const OutlineInputBorder()),
                    items: rooms
                        .map((r) => DropdownMenuItem<int>(
                              value: (r['id'] as num).toInt(),
                              child: Text('${r['room_name'] ?? r['room_number']}'),
                            ))
                        .toList(),
                    onChanged: (v) async {
                      if (v == null) return;
                      roomId = v;
                      await loadBeds();
                      setD(() {});
                    },
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<int>(
                    value: bedId == 0 ? null : bedId,
                    decoration: InputDecoration(labelText: _t('Кровать', 'Kravat'), border: const OutlineInputBorder()),
                    items: beds
                        .map((b) => DropdownMenuItem<int>(
                              value: (b['id'] as num).toInt(),
                              child: Text('${_t('Кровать', 'Kravat')} ${b['bed_number']}'),
                            ))
                        .toList(),
                    onChanged: (v) => setD(() => bedId = v ?? bedId),
                  ),
                  const SizedBox(height: 10),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(_t('Дата заезда', 'Kirish sanasi')),
                    subtitle: Text(fmt(checkin)),
                    trailing: const Icon(Icons.calendar_month),
                    onTap: () async {
                      final p = await showDatePicker(
                        context: ctx,
                        initialDate: checkin,
                        firstDate: DateTime(2020, 1, 1),
                        lastDate: DateTime(2100, 12, 31),
                      );
                      if (p != null) setD(() => checkin = p);
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(_t('Дата выезда', 'Chiqish sanasi')),
                    subtitle: Text(fmt(checkout)),
                    trailing: const Icon(Icons.calendar_month),
                    onTap: () async {
                      final p = await showDatePicker(
                        context: ctx,
                        initialDate: checkout,
                        firstDate: DateTime(2020, 1, 1),
                        lastDate: DateTime(2100, 12, 31),
                      );
                      if (p != null) setD(() => checkout = p);
                    },
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: totalCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(labelText: _t('Общая сумма', 'Jami summa'), border: const OutlineInputBorder()),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(_t('Отмена', 'Bekor'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(_t('Сохранить', 'Saqlash'))),
          ],
        ),
      ),
    );
    if (saved != true) return;
    final total = double.tryParse(totalCtrl.text.trim());
    if (total == null) {
      showAppAlert(context, _t('Неверная сумма', "Noto'g'ri summa"), error: true);
      return;
    }
    await _updateFutureBooking(
      booking: booking,
      roomId: roomId,
      bedId: bedId,
      checkinDate: fmt(checkin),
      checkoutDate: fmt(checkout),
      totalAmount: total,
    );
    if (!mounted) return;
    setState(() => _reloadDashboard());
    showAppAlert(context, _t('Будущее бронирование обновлено', 'Kelgusi bron yangilandi'));
  }

  Future<void> _openFutureBookingsForBed({
    required int roomId,
    required int bedId,
    required List<Map<String, dynamic>> seed,
    Map<String, dynamic>? bedHint,
  }) async {
    List<Map<String, dynamic>> rows = [];
    String? error;
    try {
      rows = await _loadFutureBookings(roomId, bedId, seed);
      if (rows.isEmpty && bedHint != null) {
        final checkin = _futureCheckinDate(bedHint);
        final checkout = '${bedHint['future_checkout_date'] ?? bedHint['next_checkout_date'] ?? ''}';
        final customer = '${bedHint['future_customer_name'] ?? bedHint['next_customer_name'] ?? ''}';
        if (checkin.isNotEmpty || checkout.isNotEmpty || customer.isNotEmpty) {
          rows = [
            {
              'id': bedHint['future_booking_id'] ?? bedHint['next_booking_id'] ?? 0,
              'customer_name': customer.isEmpty ? '—' : customer,
              'checkin_date': checkin,
              'checkout_date': checkout,
              'room_id': roomId,
              'bed_id': bedId,
              'total_amount': bedHint['future_total_amount'] ?? 0,
            }
          ];
        }
      }
    } catch (e) {
      error = '$e';
    }
    if (!mounted) return;
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => SafeArea(
        child: Padding(
          padding: EdgeInsets.fromLTRB(10, 10, 10, MediaQuery.of(context).viewInsets.bottom + 8),
          child: SizedBox(
            height: MediaQuery.of(context).size.height * 0.68,
            child: Column(
              children: [
                Row(
                  children: [
                    Text('🗓 ${_t('Будущие бронирования', 'Kelgusi bronlar')}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
                if (error != null)
                  Expanded(child: Center(child: Text(error!, style: const TextStyle(color: Colors.red))))
                else if (rows.isEmpty)
                  Expanded(child: Center(child: Text(_t('Будущих бронирований нет', "Kelgusi bronlar yo'q"))))
                else
                  Expanded(
                    child: ListView.separated(
                      itemCount: rows.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, i) {
                        final b = rows[i];
                        final bookingId = _asInt(b['id']) ?? 0;
                        return _Card(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('${b['customer_name'] ?? ''}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                              const SizedBox(height: 2),
                              Text(
                                '${_formatShortDate('${b['checkin_date'] ?? ''}')} → ${_formatShortDate('${b['checkout_date'] ?? ''}')}',
                                style: const TextStyle(color: Color(0xFF64748B)),
                              ),
                              const SizedBox(height: 8),
                              if (bookingId > 0)
                                Row(
                                  children: [
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        onPressed: () async {
                                          Navigator.pop(context);
                                          await _openEditFutureBooking(b);
                                        },
                                        icon: const Icon(Icons.edit, size: 16),
                                        label: Text(_t('Редактировать', 'Tahrirlash')),
                                      ),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: OutlinedButton.icon(
                                        style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5534B)),
                                        onPressed: () async {
                                          final ok = await confirmAction(
                                            context,
                                            title: _t('Отменить бронирование', 'Bronni bekor qilish'),
                                            message: _t('Подтверждаете отмену будущего бронирования?', 'Kelgusi bronni bekor qilishni tasdiqlaysizmi?'),
                                            confirmText: _t('Отменить', 'Bekor qilish'),
                                            cancelText: _t('Назад', 'Orqaga'),
                                          );
                                          if (!ok) return;
                                          await _cancelFutureBooking(b);
                                          if (!mounted) return;
                                          Navigator.pop(context);
                                          setState(() => _reloadDashboard());
                                          showAppAlert(context, _t('Будущее бронирование отменено', 'Kelgusi bron bekor qilindi'));
                                        },
                                        icon: const Icon(Icons.close, size: 16),
                                        label: Text(_t('Отменить', 'Bekor qilish')),
                                      ),
                                    ),
                                  ],
                                )
                            ],
                          ),
                        );
                      },
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _openActiveBookings() async {
    final raw = await widget.api.getJson('/active-bookings/', query: {
      'branch_id': widget.api.branchId.toString(),
    });
    if (!mounted) return;
    final all = (raw as List).cast<dynamic>();
    final search = TextEditingController();
    List<dynamic> filtered = List<dynamic>.from(all);
    String selectedRoom = '';

    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (_) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            String roomOf(Map<String, dynamic> b) =>
                '${b['room_name'] ?? b['room_number'] ?? ''}'.trim();

            void applySearch(String q) {
              final s = q.trim().toLowerCase();
              filtered = all.where((b) {
                final row = Map<String, dynamic>.from(b as Map);
                final name = '${b['customer_name'] ?? ''}'.toLowerCase();
                final passport = '${b['passport_id'] ?? ''}'.toLowerCase();
                final room = '${b['room_name'] ?? b['room_number'] ?? ''}'.toLowerCase();
                final bed = '${b['bed_number'] ?? ''}'.toLowerCase();
                final roomOk = selectedRoom.isEmpty || roomOf(row) == selectedRoom;
                final textOk = s.isEmpty ||
                    name.contains(s) ||
                    passport.contains(s) ||
                    room.contains(s) ||
                    bed.contains(s);
                return roomOk && textOk;
              }).toList();
            }

            applySearch(search.text);
            final roomOptions = all
                .map((e) => roomOf(Map<String, dynamic>.from(e as Map)))
                .where((e) => e.isNotEmpty)
                .toSet()
                .toList()
              ..sort();

            return SafeArea(
              child: Padding(
                padding: EdgeInsets.only(
                  left: 14,
                  right: 14,
                  top: 12,
                  bottom: MediaQuery.of(context).viewInsets.bottom + 10,
                ),
                child: SizedBox(
                  height: MediaQuery.of(context).size.height * 0.82,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text('🗓 ${trPair(ru: "Активные бронирования", uz: "Faol buyurtmalar")}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                          const Spacer(),
                          IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                        ],
                      ),
                      TextField(
                        controller: search,
                        onChanged: (v) => setSheetState(() => applySearch(v)),
                        decoration: InputDecoration(
                          hintText: _t('Имя, паспорт или телефон...', 'Ism, passport yoki telefon...'),
                          prefixIcon: const Icon(Icons.search),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                        ),
                      ),
                      const SizedBox(height: 10),
                      DropdownButtonFormField<String>(
                        value: selectedRoom.isEmpty ? '' : selectedRoom,
                        decoration: InputDecoration(
                          labelText: _t('Комната', 'Xona'),
                          border: OutlineInputBorder(borderRadius: BorderRadius.circular(14)),
                          isDense: true,
                          contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                        ),
                        items: [
                          DropdownMenuItem(value: '', child: Text(_t('Все комнаты', 'Barcha xonalar'))),
                          ...roomOptions.map((r) => DropdownMenuItem(value: r, child: Text(r))),
                        ],
                        onChanged: (v) => setSheetState(() {
                          selectedRoom = v ?? '';
                          applySearch(search.text);
                        }),
                      ),
                      const SizedBox(height: 10),
                      Expanded(
                        child: filtered.isEmpty
                            ? Center(child: Text(trPair(ru: 'Активные бронирования не найдены', uz: 'Faol buyurtmalar topilmadi')))
                            : ListView.separated(
                                itemCount: filtered.length,
                                separatorBuilder: (_, __) => const SizedBox(height: 10),
                                itemBuilder: (context, i) {
                                  final b = filtered[i] as Map<String, dynamic>;
                                  return Container(
                                    padding: const EdgeInsets.all(12),
                                    decoration: BoxDecoration(
                                      borderRadius: BorderRadius.circular(14),
                                      border: Border.all(color: const Color(0xFFE5E7EB)),
                                    ),
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                '👤 ${b['customer_name'] ?? ''}',
                                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
                                              ),
                                            ),
                                            Text('${b['total_amount'] ?? 0}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        Text('🪪 ${b['passport_id'] ?? ''}', style: const TextStyle(color: Colors.black54)),
                                        Text(
                                          '🏠 ${b['room_name'] ?? b['room_number']} • 🛏 ${_t("Кровать", "Kravat")} ${b['bed_number'] ?? ''}',
                                          style: const TextStyle(color: Colors.black54),
                                        ),
                                        if (b['is_hourly'] == true)
                                          Padding(
                                            padding: const EdgeInsets.only(top: 4),
                                            child: Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFFFFF4D6),
                                                borderRadius: BorderRadius.circular(999),
                                                border: Border.all(color: const Color(0xFFFCD34D)),
                                              ),
                                              child: Text(
                                                '⏱ ${_t("Почасовое бронирование", "Soatlik bron")}',
                                                style: const TextStyle(
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w700,
                                                  color: Color(0xFFB45309),
                                                ),
                                              ),
                                            ),
                                          ),
                                        Text(
                                          '🗓 ${_formatShortDate('${b['checkin_date'] ?? ''}')} → ${_formatShortDate('${b['checkout_date'] ?? ''}')}',
                                          style: const TextStyle(color: Colors.black54),
                                        ),
                                        const SizedBox(height: 8),
                                        Row(
                                          children: [
                                            Expanded(
                                              child: FilledButton.icon(
                                                onPressed: () async {
                                                  Navigator.pop(context);
                                                  await _openEditActiveBooking(b);
                                                },
                                                icon: const Icon(Icons.edit, size: 16),
                                                label: Text(_t('Редактировать', 'Tahrirlash')),
                                              ),
                                            ),
                                            const SizedBox(width: 8),
                                            Expanded(
                                              child: FilledButton.icon(
                                                style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE74C3C)),
                                                onPressed: () async {
                                                  final ok = await confirmAction(
                                                    context,
                                                    title: _t('Отменить бронирование', 'Buyurtmani bekor qilish'),
                                                    message: _t(
                                                      'Вы уверены, что хотите отменить бронирование?',
                                                      'Haqiqatan ham buyurtmani bekor qilasizmi?',
                                                    ),
                                                    confirmText: _t('Отменить', 'Bekor qilish'),
                                                    cancelText: _t('Назад', 'Orqaga'),
                                                  );
                                                  if (!ok) return;
                                                  await widget.api.postJson('/active-bookings/cancel', {
                                                    'booking_id': b['id'],
                                                    'branch_id': widget.api.branchId,
                                                  });
                                                  if (!mounted) return;
                                                  Navigator.pop(context);
                                                  setState(() => _reloadDashboard());
                                                  showAppAlert(context, _t('Бронирование отменено', 'Buyurtma bekor qilindi'));
                                                },
                                                icon: const Icon(Icons.close, size: 16),
                                                label: Text(_t('Отменить', 'Bekor qilish')),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 8),
                                        SizedBox(
                                          width: double.infinity,
                                          child: FilledButton.icon(
                                            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFF59E0B)),
                                            onPressed: () async {
                                              final ok = await confirmAction(
                                                context,
                                                title: _t('Завершить бронирование', 'Buyurtmani yakunlash'),
                                                message: _t(
                                                  'Вы уверены, что хотите завершить бронирование сейчас?',
                                                  'Haqiqatan ham buyurtmani hozir yakunlaysizmi?',
                                                ),
                                                confirmText: _t('Завершить', 'Yakunlash'),
                                                cancelText: _t('Назад', 'Orqaga'),
                                              );
                                              if (!ok) return;
                                              bool settleDebt = false;
                                              final remaining = (b['remaining_amount'] is num)
                                                  ? (b['remaining_amount'] as num).toDouble()
                                                  : double.tryParse('${b['remaining_amount'] ?? 0}') ?? 0;
                                              if (remaining > 0) {
                                                settleDebt = await confirmAction(
                                                  context,
                                                  title: _t('Есть долг', 'Qarz bor'),
                                                  message: _t(
                                                    'Долг по этому бронированию погашен? Если да, сумма долга перейдет в доход.',
                                                    'Ushbu bron bo‘yicha qarz yopildimi? Ha bo‘lsa qarz summasi daromadga qo‘shiladi.',
                                                  ),
                                                  confirmText: _t('Да, погашен', 'Ha, yopildi'),
                                                  cancelText: _t('Нет', 'Yo‘q'),
                                                );
                                              }
                                              await widget.api.postJson('/active-bookings/end', {
                                                'booking_id': b['id'],
                                                'branch_id': widget.api.branchId,
                                                'settle_debt': settleDebt,
                                              });
                                              if (!mounted) return;
                                              Navigator.pop(context);
                                              setState(() => _reloadDashboard());
                                              showAppAlert(context, _t('Бронирование завершено', 'Buyurtma yakunlandi'));
                                            },
                                            icon: const Icon(Icons.check_circle_outline, size: 16),
                                            label: Text(_t('Завершить', 'Yakunlash')),
                                          ),
                                        ),
                                      ],
                                  ),
                                );
                                },
                              ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openEditActiveBooking(Map<String, dynamic> booking) async {
    int roomId = (booking['room_id'] as num?)?.toInt() ?? 0;
    int bedId = (booking['bed_id'] as num?)?.toInt() ?? 0;
    DateTime checkin = DateTime.tryParse('${booking['checkin_date'] ?? ''}') ?? DateTime.now();
    DateTime checkout = DateTime.tryParse('${booking['checkout_date'] ?? ''}') ?? DateTime.now().add(const Duration(days: 1));
    final totalCtrl = TextEditingController(text: '${booking['total_amount'] ?? 0}');

    List<dynamic> rooms = [];
    List<dynamic> beds = [];

    Future<void> loadRooms() async {
      rooms = (await widget.api.getJson('/rooms/', query: {
        'branch_id': widget.api.branchId.toString(),
      }) as List)
          .cast<dynamic>();
      if (roomId == 0 && rooms.isNotEmpty) {
        roomId = (rooms.first['id'] as num).toInt();
      }
    }

    Future<void> loadBeds() async {
      if (roomId == 0) {
        beds = [];
        return;
      }
      beds = (await widget.api.getJson('/beds/', query: {
        'branch_id': widget.api.branchId.toString(),
        'room_id': roomId.toString(),
      }) as List)
          .cast<dynamic>();
      if (!beds.any((b) => (b['id'] as num).toInt() == bedId) && beds.isNotEmpty) {
        bedId = (beds.first['id'] as num).toInt();
      }
    }

    await loadRooms();
    await loadBeds();
    if (!mounted) return;

    String fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

    final saved = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          title: const Text('Buyurtmani tahrirlash'),
          content: SingleChildScrollView(
            child: SizedBox(
              width: 360,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  DropdownButtonFormField<int>(
                    value: roomId == 0 ? null : roomId,
                    decoration: const InputDecoration(labelText: 'Xona', border: OutlineInputBorder()),
                    items: rooms
                        .map((r) => DropdownMenuItem<int>(
                              value: (r['id'] as num).toInt(),
                              child: Text('${r['room_name'] ?? r['room_number']}'),
                            ))
                        .toList(),
                    onChanged: (v) async {
                      if (v == null) return;
                      roomId = v;
                      await loadBeds();
                      setD(() {});
                    },
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<int>(
                    value: bedId == 0 ? null : bedId,
                    decoration: const InputDecoration(labelText: 'Krovat', border: OutlineInputBorder()),
                    items: beds
                        .map((b) => DropdownMenuItem<int>(
                              value: (b['id'] as num).toInt(),
                              child: Text('Kravat ${b['bed_number']}'),
                            ))
                        .toList(),
                    onChanged: (v) => setD(() => bedId = v ?? bedId),
                  ),
                  const SizedBox(height: 10),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Kirish sanasi'),
                    subtitle: Text(fmt(checkin)),
                    trailing: const Icon(Icons.calendar_month),
                    onTap: () async {
                      final p = await showDatePicker(
                        context: ctx,
                        initialDate: checkin,
                        firstDate: DateTime(2020, 1, 1),
                        lastDate: DateTime(2100, 12, 31),
                      );
                      if (p != null) setD(() => checkin = p);
                    },
                  ),
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Chiqish sanasi'),
                    subtitle: Text(fmt(checkout)),
                    trailing: const Icon(Icons.calendar_month),
                    onTap: () async {
                      final p = await showDatePicker(
                        context: ctx,
                        initialDate: checkout,
                        firstDate: DateTime(2020, 1, 1),
                        lastDate: DateTime(2100, 12, 31),
                      );
                      if (p != null) setD(() => checkout = p);
                    },
                  ),
                  const SizedBox(height: 6),
                  TextField(
                    controller: totalCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: const InputDecoration(labelText: 'Jami summa', border: OutlineInputBorder()),
                  ),
                ],
              ),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Bekor')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Saqlash')),
          ],
        ),
      ),
    );

    if (saved != true) return;
    final total = double.tryParse(totalCtrl.text.trim());
    if (total == null) {
      showAppAlert(context, "Jami summa noto'g'ri", error: true);
      return;
    }
    await widget.api.postJson('/active-bookings/update-admin', {
      'booking_id': booking['id'],
      'room_id': roomId,
      'bed_id': bedId,
      'checkin_date': fmt(checkin),
      'checkout_date': fmt(checkout),
      'total_amount': total,
    });
    if (!mounted) return;
    setState(() => _reloadDashboard());
    showAppAlert(context, 'Buyurtma yangilandi');
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<dynamic>(
      future: _dashboardFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState != ConnectionState.done) {
          return RefreshIndicator(
            onRefresh: _pullRefresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: const [
                SizedBox(height: 260),
                Center(child: CircularProgressIndicator()),
              ],
            ),
          );
        }
        if (snapshot.hasError) {
          return RefreshIndicator(
            onRefresh: _pullRefresh,
            child: ListView(
              physics: const AlwaysScrollableScrollPhysics(),
              children: [
                SizedBox(
                  height: 360,
                  child: _ErrorText(error: snapshot.error.toString()),
                )
              ],
            ),
          );
        }
        final rooms = (snapshot.data as List).cast<dynamic>();
        return RefreshIndicator(
          onRefresh: _pullRefresh,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.all(16),
            children: [
              _Card(
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '🏨 ${_t("Доступность комнат", "Xona mavjudligi")}',
                            style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                          ),
                        ),
                        FilledButton.icon(
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF3D8BDF),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          onPressed: _openActiveBookings,
                          icon: const Icon(Icons.calendar_month, size: 18),
                          label: Text(_t('Активные бронирования', 'Faol buyurtmalar')),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _DateBox(
                            value: _fmt(_fromDate),
                            onTap: () => _pickDate(true),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 8),
                          child: Text('—', style: TextStyle(fontSize: 24, color: Color(0xFF6B7280))),
                        ),
                        Expanded(
                          child: _DateBox(
                            value: _fmt(_toDate),
                            onTap: () => _pickDate(false),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    Row(
                      children: [
                        Expanded(
                          child: FilledButton.icon(
                            style: FilledButton.styleFrom(
                              backgroundColor: const Color(0xFF3D8BDF),
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                              padding: const EdgeInsets.symmetric(vertical: 11),
                            ),
                            onPressed: _applyFilter,
                            icon: const Icon(Icons.search, size: 18),
                            label: Text(_t("поиск", "izlash"), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                          ),
                        ),
                        const SizedBox(width: 10),
                        OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(color: Color(0xFFF87171)),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 11),
                          ),
                          onPressed: _clearFilter,
                          child: const Icon(Icons.close, color: Color(0xFFEF4444), size: 20),
                        ),
                      ],
                    ),
                    if (_hasActiveFilter) ...[
                      const SizedBox(height: 10),
                      Container(
                        width: double.infinity,
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F3FF),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFBFDBFE)),
                        ),
                        child: Text(
                          "${_t('Фильтр активен', 'Filter active')}: ${_fmt(_appliedFromDate!)} - ${_fmt(_appliedToDate!)}",
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: Color(0xFF1E3A8A)),
                        ),
                      ),
                    ]
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (rooms.isEmpty) _EmptyState(_t('В этом диапазоне свободных мест нет.', 'Bu vaqt oralig‘ida bo‘sh joy topilmadi.')),
              ...rooms.map((r) {
              final beds = (r['beds'] as List? ?? const []);
              return Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: _Card(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('🏠 ${r['room_name'] ?? r['room_number']}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: beds.map<Widget>((b) {
                          final bed = Map<String, dynamic>.from(b as Map);
                          final busy = bed['is_busy'] == true;
                          final futureRows = _extractFutureBookings(bed);
                          final hasFuture = _hasFutureHint(bed, futureRows);
                          final targetDate = busy
                              ? '${bed['checkout_date'] ?? ''}'
                              : _futureCheckinDate(bed);
                          final time = _timeLeft(
                            targetDate,
                            dateOnlyAsEndOfDay: busy,
                          );
                          final roomId = _asInt(r['room_id'] ?? r['id'] ?? r['roomId'] ?? r['room']) ?? 0;
                          final bedId = _asInt(
                                bed['bed_id'] ??
                                    bed['id'] ??
                                    bed['bedId'] ??
                                    bed['bedID'] ??
                                    bed['bed'],
                              ) ??
                              _asInt(bed['bed_number']) ??
                              0;
                          final hasFutureFromIndex = bedId > 0 && (_futureByBed[bedId] ?? 0) > 0;
                          final hasFutureFinal = hasFuture || hasFutureFromIndex;
                          final bookedLikeFinal = busy;

                          return GestureDetector(
                            behavior: HitTestBehavior.opaque,
                            onTap: () => _openFutureBookingsForBed(
                              roomId: roomId,
                              bedId: bedId,
                              seed: futureRows,
                              bedHint: bed,
                            ),
                            child: Stack(
                              children: [
                                Container(
                                width: 132,
                                padding: const EdgeInsets.all(8),
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(12),
                                    color: bookedLikeFinal ? const Color(0xFFFFF1F2) : const Color(0xFFECFDF3),
                                  border: Border.all(
                                    color: bookedLikeFinal ? const Color(0xFFFCA5A5) : const Color(0xFF86EFAC),
                                  ),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '${_t("Кровать", "Kravat")} ${bed['bed_number']}',
                                      style: TextStyle(
                                        fontSize: 13,
                                        fontWeight: FontWeight.w700,
                                        color: bookedLikeFinal ? const Color(0xFFB91C1C) : const Color(0xFF166534),
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        _MiniTime(value: time['d']!, label: _t('Дни', 'Kunlar')),
                                        _MiniTime(value: time['h']!, label: _t('Часы', 'Soatlar')),
                                      ],
                                    ),
                                    Row(
                                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                      children: [
                                        _MiniTime(value: time['m']!, label: _t('Минуты', 'Minutlar')),
                                        _MiniTime(value: time['s']!, label: _t('Секунды', 'Sekundlar')),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      busy
                                          ? '${_bedTypeEmoji('${bed['bed_type'] ?? 'single'}')} ⏱ ${_formatShortDate('${bed['checkout_date'] ?? ''}')}'
                                          : '${_bedTypeEmoji('${bed['bed_type'] ?? 'single'}')} ✔ ${_t("Свободно", "Bo'sh")}',
                                      style: TextStyle(
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                        color: bookedLikeFinal ? const Color(0xFFB91C1C) : const Color(0xFF166534),
                                      ),
                                    ),
                                    if (busy && bed['is_hourly'] == true)
                                      Container(
                                        margin: const EdgeInsets.only(top: 4),
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: const Color(0xFFFFF4D6),
                                          borderRadius: BorderRadius.circular(999),
                                          border: Border.all(color: const Color(0xFFFCD34D)),
                                        ),
                                        child: Text(
                                          '⏱ ${_t("Почасовая", "Soatlik")}',
                                          style: const TextStyle(
                                            fontSize: 10,
                                            fontWeight: FontWeight.w700,
                                            color: Color(0xFFB45309),
                                          ),
                                        ),
                                      ),
                                  ],
                                ),
                              ),
                                if (hasFutureFinal && bedId > 0)
                                  Positioned(
                                    top: 3,
                                    right: 3,
                                    child: Container(
                                      height: 20,
                                      width: 20,
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFDBEAFE),
                                        borderRadius: BorderRadius.circular(10),
                                      ),
                                      child: const Icon(Icons.calendar_month, size: 12, color: Color(0xFF2563EB)),
                                    ),
                                  ),
                              ],
                            ),
                          );
                        }).toList(),
                      ),
                    ],
                  ),
                ),
              );
            }),
            ],
          ),
        );
      },
    );
  }
}

class _DateBox extends StatelessWidget {
  const _DateBox({required this.value, required this.onTap});
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFD1D5DB)),
          color: Colors.white,
        ),
        child: Row(
          children: [
            Expanded(child: Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
            const Icon(Icons.calendar_month, size: 16),
          ],
        ),
      ),
    );
  }
}

class _MiniTime extends StatelessWidget {
  const _MiniTime({required this.value, required this.label});
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
        Text(label, style: const TextStyle(fontSize: 10, color: Color(0xFF475467))),
      ],
    );
  }
}

class _RoomsPage extends StatefulWidget {
  const _RoomsPage({required this.api, required this.onDataChanged});
  final _ApiClient api;
  final VoidCallback onDataChanged;

  @override
  State<_RoomsPage> createState() => _RoomsPageState();
}

class _RoomsPageState extends State<_RoomsPage> {
  bool _loading = true;
  bool _savingRoomSettings = false;
  String? _error;
  List<dynamic> _rooms = [];
  List<dynamic> _selectedRoomBeds = [];
  List<Map<String, dynamic>> _roomImages = [];
  int? _selectedRoomId;
  int? _selectedBedId;
  String _selectedRoomType = 'bed';
  String _selectedBookingMode = 'bed';
  bool _imagesLoading = false;
  bool _uploadingImage = false;
  final ImagePicker _imagePicker = ImagePicker();
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz);

  int? _toInt(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse('${v ?? ''}');
  }

  @override
  void initState() {
    super.initState();
    _loadRooms();
  }

  Future<void> _loadRooms() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/rooms/', query: {
        'branch_id': widget.api.branchId.toString(),
      });
      final rooms = (data as List).cast<dynamic>();
      setState(() {
        _rooms = rooms;
        if (_selectedRoomId == null && rooms.isNotEmpty) {
          _selectedRoomId = _toInt(rooms.first['id']);
        } else if (_selectedRoomId != null &&
            !rooms.any((r) => _toInt(r['id']) == _selectedRoomId)) {
          _selectedRoomId = rooms.isNotEmpty ? _toInt(rooms.first['id']) : null;
        }
        _selectedBedId = null;
        _selectedRoomBeds = [];
        _syncSelectedRoomSettings();
      });
      await _loadBedsForSelectedRoom();
      await _loadImagesForSelectedRoom();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  dynamic get _selectedRoom {
    if (_selectedRoomId == null) return null;
    for (final r in _rooms) {
      if (_toInt(r['id']) == _selectedRoomId) return r;
    }
    return null;
  }

  String _normalizeRoomType(dynamic value) {
    final v = '${value ?? ''}'.trim().toLowerCase();
    if (v == 'family' || v.contains('oilav') || v.contains('сем')) return 'family';
    if (v == 'other' || v.contains('boshqa') || v.contains('друг')) return 'other';
    return 'bed';
  }

  String _normalizeBookingMode(dynamic value) {
    final v = '${value ?? ''}'.trim().toLowerCase();
    return v == 'full' ? 'full' : 'bed';
  }

  void _syncSelectedRoomSettings() {
    final room = _selectedRoom;
    if (room == null) {
      _selectedRoomType = 'bed';
      _selectedBookingMode = 'bed';
      return;
    }
    _selectedRoomType = _normalizeRoomType(room['room_type']);
    _selectedBookingMode = _normalizeBookingMode(room['booking_mode']);
  }

  String _roomTypeUi(String v) {
    switch (v) {
      case 'family':
        return _t('Семейный', 'Oilaviy');
      case 'other':
        return _t('Другое', 'Boshqa');
      default:
        return _t('Кровати', 'Kravat bo‘yicha');
    }
  }

  String _bookingModeUi(String v) {
    return v == 'full' ? _t('Полная комната', 'To‘liq xona') : _t('По кроватям', 'Kravat bo‘yicha');
  }

  Future<void> _loadBedsForSelectedRoom() async {
    final roomId = _selectedRoomId;
    if (roomId == null) {
      setState(() => _selectedRoomBeds = []);
      return;
    }
    try {
      final data = await widget.api.getJson('/beds/', query: {
        'branch_id': widget.api.branchId.toString(),
        'room_id': roomId.toString(),
      });
      setState(() {
        _selectedRoomBeds = (data as List).cast<dynamic>();
      });
    } catch (e) {
      setState(() {
        _selectedRoomBeds = [];
      });
      _showSnack("${_t('Не удалось загрузить кровати', "Krovatlarni yuklab bo'lmadi")}: $e");
    }
  }

  Future<void> _loadImagesForSelectedRoom() async {
    final roomId = _selectedRoomId;
    if (roomId == null) {
      if (mounted) setState(() => _roomImages = []);
      return;
    }
    if (mounted) setState(() => _imagesLoading = true);
    try {
      final rows = await widget.api.listRoomImages(roomId);
      if (!mounted) return;
      setState(() => _roomImages = rows);
    } catch (e) {
      if (!mounted) return;
      setState(() => _roomImages = []);
      _showSnack(
        "${_t('Не удалось загрузить фото комнаты', 'Xona rasmlarini yuklab bo‘lmadi')}: $e",
        error: true,
      );
    } finally {
      if (mounted) setState(() => _imagesLoading = false);
    }
  }

  String _imageUrl(dynamic imagePath) {
    final raw = '${imagePath ?? ''}'.trim();
    if (raw.isEmpty) return '';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    if (raw.startsWith('/')) return 'https://hmsuz.com$raw';
    return 'https://hmsuz.com/$raw';
  }

  Future<void> _pickAndUploadRoomImage() async {
    final roomId = _selectedRoomId;
    if (roomId == null) {
      _showSnack(_t('Сначала выберите комнату.', 'Avval xona tanlang.'));
      return;
    }
    final picked = await _imagePicker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 88,
      maxWidth: 1800,
    );
    if (picked == null) return;
    setState(() => _uploadingImage = true);
    try {
      await widget.api.uploadRoomImage(
        roomId,
        filePath: picked.path,
        isCover: _roomImages.isEmpty,
      );
      await _loadImagesForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t('Фото загружено.', 'Rasm yuklandi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    } finally {
      if (mounted) setState(() => _uploadingImage = false);
    }
  }

  Future<void> _setCoverImage(Map<String, dynamic> image) async {
    final roomId = _selectedRoomId;
    final imageId = _toInt(image['id']);
    if (roomId == null || imageId == null) return;
    try {
      await widget.api.setRoomImageCover(roomId, imageId);
      await _loadImagesForSelectedRoom();
      _showSnack(_t('Обложка обновлена.', 'Muqova yangilandi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _deleteRoomImage(Map<String, dynamic> image) async {
    final roomId = _selectedRoomId;
    final imageId = _toInt(image['id']);
    if (roomId == null || imageId == null) return;
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t('Удалить фото', 'Rasmni o‘chirish')),
        content: Text(_t('Удалить выбранное фото комнаты?', 'Tanlangan xona rasmini o‘chirasizmi?')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Удалить', "O'chirish"))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.api.deleteRoomImage(roomId, imageId);
      await _loadImagesForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t('Фото удалено.', 'Rasm o‘chirildi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _addRoomDialog() async {
    final c = TextEditingController();
    final daily = TextEditingController();
    final hourly = TextEditingController();
    final monthly = TextEditingController();
    String roomType = 'other';
    String bookingMode = 'bed';

    double? _toNullableNum(String raw) {
      final s = raw.trim();
      if (s.isEmpty) return null;
      return double.tryParse(s);
    }

    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (context, setStateDialog) => AlertDialog(
          title: Text(_t('Добавить комнату', "Xona qo'shish")),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: c,
                  decoration: InputDecoration(
                    labelText: _t('Название комнаты', 'Xona nomi'),
                    hintText: _t('Введите название комнаты', 'Xona nomini kiriting'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: roomType,
                  decoration: InputDecoration(
                    labelText: _t('Тип комнаты', 'Xona turi'),
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    DropdownMenuItem(value: 'other', child: Text(_t('Другое', 'Boshqa'))),
                    DropdownMenuItem(value: 'bed', child: Text(_t('Кровати', 'Kravat bo‘yicha'))),
                    DropdownMenuItem(value: 'family', child: Text(_t('Семейная', 'Oilaviy'))),
                  ],
                  onChanged: (v) => setStateDialog(() => roomType = v ?? 'other'),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<String>(
                  value: bookingMode,
                  decoration: InputDecoration(
                    labelText: _t('Режим бронирования', 'Bron rejimi'),
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    DropdownMenuItem(value: 'bed', child: Text(_t('Частично (по кроватям)', 'Qisman (kravat bo‘yicha)'))),
                    DropdownMenuItem(value: 'full', child: Text(_t('Полная комната', 'To‘liq xona'))),
                  ],
                  onChanged: (v) => setStateDialog(() => bookingMode = v ?? 'bed'),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: daily,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: _t('За день (необязательно)', 'Kunlik / За день (ixtiyoriy)'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: hourly,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: _t('За час', 'Soatlik / За час'),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: monthly,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: _t('За месяц', 'Oylik / За месяц'),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor'))),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Создать', "Yaratish"))),
          ],
        ),
      ),
    );
    if (ok != true) return;
    final name = c.text.trim();
    if (name.isEmpty) return;

    final usedNumbers = <String>{};
    for (final r in _rooms) {
      final value = '${r['room_number'] ?? r['number'] ?? ''}'.trim();
      if (value.isNotEmpty) usedNumbers.add(value);
    }
    var candidate = 1;
    while (usedNumbers.contains(candidate.toString())) {
      candidate += 1;
    }
    final nextNumber = candidate.toString();

    try {
      await widget.api.postJson('/rooms/', {
        'branch_id': widget.api.branchId,
        'number': nextNumber,
        'room_name': name,
        'room_type': roomType,
        'booking_mode': bookingMode,
        'price_daily': _toNullableNum(daily.text),
        'price_hourly': _toNullableNum(hourly.text),
        'price_monthly': _toNullableNum(monthly.text),
      });
      await _loadRooms();
      widget.onDataChanged();
      _showSnack(_t('Комната добавлена.', "Xona qo'shildi."));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _deleteSelectedRoom() async {
    final room = _selectedRoom;
    if (room == null) return;
    final roomId = _toInt(room['id']);
    if (roomId == null) {
      _showSnack(_t('Некорректный ID комнаты.', "Xona ID noto'g'ri."), error: true);
      return;
    }
    final has = await widget.api.getJson('/rooms/$roomId/has-bookings', query: {
      'branch_id': widget.api.branchId.toString(),
    });
    if (has is Map && has['has_booking'] == true) {
      _showSnack(_t('В этой комнате есть брони, удалить нельзя.', 'Bu xonada bronlar bor, o‘chirib bo‘lmaydi.'), error: true);
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t("Удалить комнату", "Xonani o'chirish")),
        content: Text(_t('Вы уверены, что хотите удалить комнату?', "Haqiqatan ham xonani o‘chirasizmi?")),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Нет', 'Yo‘q'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Да', 'Ha'))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await widget.api.deleteJson('/rooms/$roomId', query: {
        'branch_id': widget.api.branchId.toString(),
      });
      await _loadRooms();
      widget.onDataChanged();
      _showSnack(_t("Комната удалена.", "Xona o'chirildi."));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _saveSelectedRoomSettings() async {
    final room = _selectedRoom;
    final roomId = room == null ? null : _toInt(room['id']);
    if (roomId == null) return;
    if (_savingRoomSettings) return;
    setState(() => _savingRoomSettings = true);
    try {
      await widget.api.putQuery('/rooms/$roomId/type', {
        'branch_id': widget.api.branchId.toString(),
        'room_type': _selectedRoomType,
      });
      await widget.api.putQuery('/rooms/$roomId/booking-mode', {
        'branch_id': widget.api.branchId.toString(),
        'booking_mode': _selectedBookingMode,
      });
      await _loadRooms();
      widget.onDataChanged();
      _showSnack(_t('Настройки комнаты сохранены.', 'Xona sozlamalari saqlandi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    } finally {
      if (mounted) setState(() => _savingRoomSettings = false);
    }
  }

  Future<void> _bulkSetSelectedRoomBedsPrice() async {
    final roomId = _selectedRoomId;
    if (roomId == null) {
      _showSnack(_t('Сначала выберите комнату.', 'Avval xona tanlang.'));
      return;
    }
    final daily = TextEditingController();
    final hourly = TextEditingController();
    final monthly = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t('Цены для всех кроватей', 'Barcha kravat narxi')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: daily,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: _t('За день (необязательно)', 'Kunlik (ixtiyoriy)'),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: hourly,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: _t('За час (необязательно)', 'Soatlik (ixtiyoriy)'),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: monthly,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: _t('За месяц (необязательно)', 'Oylik (ixtiyoriy)'),
                border: const OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _t(
                'Будут применены только заполненные поля.',
                "Faqat to'ldirilgan maydonlar qo'llanadi.",
              ),
              style: const TextStyle(fontSize: 12, color: Colors.black54),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Применить', "Qo'llash"))),
        ],
      ),
    );
    if (ok != true) return;

    final q = <String, String>{
      'branch_id': widget.api.branchId.toString(),
      'price_daily': daily.text.trim(),
      'price_hourly': hourly.text.trim(),
      'price_monthly': monthly.text.trim(),
    };
    if (q['price_daily']!.isEmpty && q['price_hourly']!.isEmpty && q['price_monthly']!.isEmpty) {
      _showSnack(_t('Заполните хотя бы одно поле.', "Kamida bitta maydonni to'ldiring."));
      return;
    }
    try {
      await widget.api.putQuery('/beds/room/$roomId/bulk-price', q);
      await _loadBedsForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t('Цены кроватей обновлены.', 'Kravat narxlari yangilandi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _addBed() async {
    final roomId = _selectedRoomId;
    if (roomId == null) {
      _showSnack(_t('Сначала выберите комнату.', 'Avval xona tanlang.'));
      return;
    }
    try {
      await widget.api.postJson('/beds/', {
        'branch_id': widget.api.branchId,
        'room_id': roomId,
      });
      await _loadBedsForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t('Кровать добавлена.', "Kravat qo'shildi."));
    } catch (e) {
      _showSnack("${_t('Не удалось добавить кровать', "Kravat qo'shib bo'lmadi")}: $e", error: true);
    }
  }

  Future<void> _deleteBed(Map<String, dynamic> bed) async {
    final bedId = _toInt(bed['id']);
    if (bedId == null) {
      _showSnack(_t('Некорректный ID кровати.', "Krovat ID noto'g'ri."), error: true);
      return;
    }
    final busy = await widget.api.getJson('/beds/$bedId/has-bookings', query: {
      'branch_id': widget.api.branchId.toString(),
    });
    if (busy is Map && busy['has_booking'] == true) {
      _showSnack(_t('На этой кровати есть бронь, удалить нельзя.', 'Bu krovatda bron bor, o‘chirib bo‘lmaydi.'), error: true);
      return;
    }
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t("Удалить кровать", "Krovatni o'chirish")),
        content: Text("${_t('Удалить кровать', 'Kravat')} ${bed['bed_number']}?"),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Удалить', "O'chirish"))),
        ],
      ),
    );
    if (ok != true) {
      return;
    }
    try {
      await widget.api.deleteJson('/beds/$bedId');
      await _loadBedsForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t("Кровать удалена.", "Krovat o'chirildi."));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  Future<void> _editBedType(Map<String, dynamic> bed) async {
    String type = '${bed['bed_type'] ?? 'single'}';
    final daily = TextEditingController(text: '${bed['price_daily'] ?? ''}'.replaceAll('.0', ''));
    final hourly = TextEditingController(text: '${bed['price_hourly'] ?? ''}'.replaceAll('.0', ''));
    final monthly = TextEditingController(text: '${bed['price_monthly'] ?? ''}'.replaceAll('.0', ''));
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (context, setStateDialog) => AlertDialog(
          title: Text(_t('Редактировать кровать', 'Kravatni tahrirlash')),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                DropdownButtonFormField<String>(
                  value: type,
                  items: [
                    DropdownMenuItem(value: 'single', child: Text(_t('Одноместная', 'Bir kishilik'))),
                    DropdownMenuItem(value: 'double', child: Text(_t('Двухместная', 'Ikki kishilik'))),
                    DropdownMenuItem(value: 'child', child: Text(_t('Детская', 'Bolalar'))),
                  ],
                  onChanged: (v) => setStateDialog(() => type = v ?? 'single'),
                  decoration: InputDecoration(
                    labelText: _t('Тип кровати', 'Kravat turi'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: daily,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                    labelText: _t('За день (необязательно)', 'Kunlik / За день (ixtiyoriy)'),
                    border: const OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: hourly,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: _t('За час', 'Soatlik / За час'),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: monthly,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText: _t('За месяц', 'Oylik / За месяц'),
                          border: const OutlineInputBorder(),
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor'))),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Сохранить', 'Saqlash'))),
          ],
        ),
      ),
    );
    if (ok != true) return;

    try {
      await widget.api.putQuery('/beds/${bed['id']}', {
        'bed_number': '${bed['bed_number']}',
        'bed_type': type,
        'price_daily': daily.text.trim(),
        'price_hourly': hourly.text.trim(),
        'price_monthly': monthly.text.trim(),
      });
      await _loadBedsForSelectedRoom();
      widget.onDataChanged();
      _showSnack(_t('Кровать обновлена.', 'Kravat yangilandi.'));
    } catch (e) {
      _showSnack('$e', error: true);
    }
  }

  void _showBedActions(Map<String, dynamic> bed) {
    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (_) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              leading: const Icon(Icons.edit),
              title: Text(_t('Изменить тип кровати', 'Krovat turini o‘zgartirish')),
              onTap: () {
                Navigator.pop(context);
                _editBedType(bed);
              },
            ),
            ListTile(
              leading: const Icon(Icons.delete, color: Colors.red),
              title: Text(_t("Удалить кровать", "Krovatni o'chirish")),
              onTap: () {
                Navigator.pop(context);
                _deleteBed(bed);
              },
            ),
          ],
        ),
      ),
    );
  }

  String _bedTypeLabel(String t) {
    switch (t) {
      case 'double':
        return _t('Двухместная\nкровать', 'Ikki kishilik\nkrovat');
      case 'child':
        return _t('Детская\nкровать', 'Bolalar\nkrovati');
      default:
        return _t('Одноместная\nкровать', 'Bir kishilik\nkrovat');
    }
  }

  String _bedTypeEmoji(String t) {
    switch (t) {
      case 'double':
        return '👥';
      case 'child':
        return '🧸';
      default:
        return '👤';
    }
  }

  void _showSnack(String text, {bool error = false}) {
    showAppAlert(context, text, error: error);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return RefreshIndicator(
        onRefresh: _loadRooms,
        child: ListView(
          physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
          children: [
            const SizedBox(height: 140),
            _ErrorText(error: _error!),
            const SizedBox(height: 10),
            Center(
              child: Text(
                _t('Потяните вниз, чтобы обновить', 'Yangilash uchun pastga torting'),
                style: const TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
    }
    final room = _selectedRoom;
    final beds = _selectedRoomBeds.cast<dynamic>();
    Map<String, dynamic>? selectedBed;
    for (final b in beds) {
      if ((b['id'] as num).toInt() == _selectedBedId) {
        selectedBed = Map<String, dynamic>.from(b as Map);
        break;
      }
    }

    return RefreshIndicator(
      onRefresh: _loadRooms,
      child: ListView(
        physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
        padding: const EdgeInsets.all(16),
        children: [
          _SectionTitle(_t('Комнаты и кровати', 'Xonalar va yotoqlar')),
          const SizedBox(height: 10),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(_t('Комнаты', 'Honalar'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    Container(
                      margin: const EdgeInsets.only(right: 8),
                      decoration: BoxDecoration(
                        color: const Color(0xFFE8F2FF),
                        shape: BoxShape.circle,
                        border: Border.all(color: const Color(0xFFBFD6FB)),
                      ),
                      child: IconButton(
                        onPressed: _selectedRoomId == null ? null : _bulkSetSelectedRoomBedsPrice,
                        icon: const Text('💸', style: TextStyle(fontSize: 18)),
                        tooltip: _t('Цены для всех кроватей', 'Barcha kravat narxi'),
                      ),
                    ),
                    Container(
                      decoration: const BoxDecoration(
                        color: Color(0xFF3D8BDF),
                        shape: BoxShape.circle,
                      ),
                      child: IconButton(
                        onPressed: _addRoomDialog,
                        icon: const Icon(Icons.add, color: Colors.white),
                        tooltip: _t('Добавить комнату', "Xona qo'shish"),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _rooms.map((r) {
                    final id = _toInt(r['id']);
                    if (id == null) return const SizedBox.shrink();
                    final selected = id == _selectedRoomId;
                    return ChoiceChip(
                      label: Text('🏠 ${r['room_name'] ?? r['room_number']}'),
                      selected: selected,
                      onSelected: (_) async {
                        setState(() {
                          _selectedRoomId = id;
                          _selectedBedId = null;
                          _selectedRoomBeds = [];
                          _syncSelectedRoomSettings();
                        });
                        await _loadBedsForSelectedRoom();
                        await _loadImagesForSelectedRoom();
                      },
                    );
                  }).toList(),
                ),
                const SizedBox(height: 10),
                if (room != null) ...[
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _selectedRoomType,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                          ),
                          items: [
                            DropdownMenuItem(value: 'bed', child: Text(_roomTypeUi('bed'))),
                            DropdownMenuItem(value: 'family', child: Text(_roomTypeUi('family'))),
                            DropdownMenuItem(value: 'other', child: Text(_roomTypeUi('other'))),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => _selectedRoomType = v);
                          },
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _selectedBookingMode,
                          decoration: const InputDecoration(
                            border: OutlineInputBorder(),
                          ),
                          items: [
                            DropdownMenuItem(value: 'bed', child: Text(_bookingModeUi('bed'))),
                            DropdownMenuItem(value: 'full', child: Text(_bookingModeUi('full'))),
                          ],
                          onChanged: (v) {
                            if (v == null) return;
                            setState(() => _selectedBookingMode = v);
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      Expanded(
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF2B7CCF)),
                          onPressed: _savingRoomSettings ? null : _saveSelectedRoomSettings,
                          icon: _savingRoomSettings
                              ? const SizedBox(
                                  width: 14,
                                  height: 14,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                                )
                              : const Icon(Icons.save_outlined),
                          label: Text(_t('Сохранить', 'Saqlash')),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: FilledButton.icon(
                          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE53935)),
                          onPressed: _deleteSelectedRoom,
                          icon: const Icon(Icons.delete),
                          label: Text(_t("Удалить комнату", "Xonani o'chirish")),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 12),
          if (room != null)
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        _t('Фото комнаты', 'Xona rasmlari'),
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                      const Spacer(),
                      FilledButton.icon(
                        onPressed: _uploadingImage ? null : _pickAndUploadRoomImage,
                        icon: _uploadingImage
                            ? const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.upload_outlined),
                        label: Text(_t('Загрузить', 'Yuklash')),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _t(
                      'Схема: выберите комнату -> загрузите фото -> при необходимости сделайте обложкой или удалите.',
                      'Tartib: xona tanlang -> rasm yuklang -> kerak bo‘lsa muqova qiling yoki o‘chiring.',
                    ),
                    style: const TextStyle(color: Color(0xFF475467), fontSize: 12.5),
                  ),
                  const SizedBox(height: 10),
                  if (_imagesLoading) const LinearProgressIndicator(minHeight: 3),
                  if (!_imagesLoading && _roomImages.isEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        _t('Фото пока нет.', 'Hozircha rasm yo‘q.'),
                        style: const TextStyle(color: Colors.black54),
                      ),
                    ),
                  if (_roomImages.isNotEmpty)
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: _roomImages.map((img) {
                        final isCover = img['is_cover'] == true;
                        final url = _imageUrl(img['image_path']);
                        return Container(
                          width: 140,
                          decoration: BoxDecoration(
                            border: Border.all(
                              color: isCover ? const Color(0xFF1D4ED8) : const Color(0xFFE2E8F0),
                              width: isCover ? 2 : 1,
                            ),
                            borderRadius: BorderRadius.circular(12),
                            color: Colors.white,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              ClipRRect(
                                borderRadius: const BorderRadius.vertical(top: Radius.circular(10)),
                                child: Container(
                                  color: const Color(0xFFF1F5F9),
                                  height: 90,
                                  child: url.isEmpty
                                      ? const Icon(Icons.image_not_supported_outlined)
                                      : Image.network(
                                          url,
                                          fit: BoxFit.cover,
                                          errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_outlined),
                                        ),
                                ),
                              ),
                              Padding(
                                padding: const EdgeInsets.fromLTRB(6, 6, 6, 6),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: isCover
                                          ? Container(
                                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFFE0ECFF),
                                                borderRadius: BorderRadius.circular(999),
                                              ),
                                              child: Text(
                                                _t('Обложка', 'Muqova'),
                                                textAlign: TextAlign.center,
                                                style: const TextStyle(
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w700,
                                                  color: Color(0xFF1E40AF),
                                                ),
                                              ),
                                            )
                                          : OutlinedButton(
                                              onPressed: () => _setCoverImage(img),
                                              style: OutlinedButton.styleFrom(
                                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                              ),
                                              child: Text(
                                                _t('Сделать', 'Muqova'),
                                                style: const TextStyle(fontSize: 11),
                                              ),
                                            ),
                                    ),
                                    const SizedBox(width: 4),
                                    IconButton(
                                      onPressed: () => _deleteRoomImage(img),
                                      icon: const Icon(Icons.delete_outline, color: Color(0xFFDC2626)),
                                      tooltip: _t('Удалить фото', 'Rasmni o‘chirish'),
                                      constraints: const BoxConstraints(minHeight: 30, minWidth: 30),
                                      padding: EdgeInsets.zero,
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      }).toList(),
                    ),
                ],
              ),
            ),
          const SizedBox(height: 12),
          if (room == null) _EmptyState(_t('Комната не выбрана.', 'Xona tanlanmagan.')),
          if (room != null)
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text('${room['room_number'] ?? room['room_name']} — ${_t("Кровати", "Kravatlar")}',
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      const Spacer(),
                      Container(
                        margin: const EdgeInsets.only(right: 8),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F2FF),
                          shape: BoxShape.circle,
                          border: Border.all(color: const Color(0xFFBFD6FB)),
                        ),
                        child: IconButton(
                          onPressed: _bulkSetSelectedRoomBedsPrice,
                          icon: const Text('💸', style: TextStyle(fontSize: 18)),
                          tooltip: _t('Цены для всех кроватей', 'Barcha kravat narxi'),
                        ),
                      ),
                      Container(
                        decoration: const BoxDecoration(
                          color: Color(0xFF3D8BDF),
                          shape: BoxShape.circle,
                        ),
                        child: IconButton(
                          onPressed: _addBed,
                          icon: const Icon(Icons.add, color: Colors.white),
                          tooltip: _t('Добавить кровать', "Krovat qo'shish"),
                        ),
                      ),
                    ],
                  ),
                  if (beds.isEmpty) Padding(
                    padding: EdgeInsets.only(top: 8),
                    child: Text(_t('Кроватей нет', 'Krovat yo‘q'), style: const TextStyle(color: Colors.black54)),
                  ),
                  if (beds.isNotEmpty)
                    Wrap(
                      spacing: 10,
                      runSpacing: 10,
                      children: beds.map<Widget>((b) {
                        final bed = Map<String, dynamic>.from(b as Map);
                        final bedId = _toInt(bed['id']);
                        final selected = _selectedBedId == bedId;
                        final busy = bed['is_busy'] == true;
                        return InkWell(
                          onTap: () => setState(() {
                            _selectedBedId = bedId;
                          }),
                          onLongPress: () => _showBedActions(bed),
                          child: Container(
                            width: 150,
                            padding: const EdgeInsets.all(10),
                            decoration: BoxDecoration(
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: selected
                                    ? const Color(0xFF3D8BDF)
                                    : (busy ? const Color(0xFFFCA5A5) : const Color(0xFF86EFAC)),
                                width: selected ? 2 : 1,
                              ),
                              color: busy ? const Color(0xFFFFF1F2) : const Color(0xFFECFDF3),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Align(
                                  alignment: Alignment.topRight,
                                  child: Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                                    decoration: BoxDecoration(
                                      color: busy ? const Color(0xFFEF5350) : const Color(0xFF22C55E),
                                      borderRadius: BorderRadius.circular(999),
                                    ),
                                    child: Text(
                                      busy ? _t('Занято', 'Band') : _t('Свободно', "Bo'sh"),
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12),
                                    ),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Center(
                                  child: Text(
                                    _bedTypeEmoji('${bed['bed_type'] ?? 'single'}'),
                                    style: const TextStyle(fontSize: 34),
                                  ),
                                ),
                                const SizedBox(height: 8),
                                Center(
                                  child: Text(
                                    _bedTypeLabel('${bed['bed_type'] ?? 'single'}'),
                                    textAlign: TextAlign.center,
                                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Center(
                                  child: Text(
                                    '${_t("Кровать", "Kravat")} ${bed['bed_number']}',
                                    style: const TextStyle(color: Colors.black54, fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      }).toList(),
                    ),
                  const SizedBox(height: 12),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE53935)),
                      onPressed: selectedBed == null ? null : () => _deleteBed(selectedBed!),
                      icon: const Icon(Icons.delete),
                      label: Text(_t("Удалить кровать", "Krevatni o'chirish")),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF2B7CCF)),
                      onPressed: selectedBed == null ? null : () => _editBedType(selectedBed!),
                      icon: const Icon(Icons.edit),
                      label: Text(_t("Редактировать кровать", "Krovatni tahrirlash")),
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _BookingsPage extends StatefulWidget {
  const _BookingsPage({required this.api, required this.onDataChanged});
  final _ApiClient api;
  final VoidCallback onDataChanged;

  @override
  State<_BookingsPage> createState() => _BookingsPageState();
}

class _BookingsPageState extends State<_BookingsPage> {
  bool _loading = true;
  bool _saving = false;
  String? _error;
  String? _dateError;

  List<dynamic> _rooms = [];
  List<dynamic> _customers = [];
  List<dynamic> _availableBeds = [];
  List<dynamic> _customerSuggestions = [];

  int? _roomId;
  Map<String, dynamic>? _selectedBed;
  bool _secondGuestEnabled = false;
  bool _isHourlyBooking = false;

  DateTime _checkin = DateTime.now();
  DateTime _checkout = DateTime.now().add(const Duration(days: 1));
  DateTime _notifyDate = DateTime.now().add(const Duration(days: 1));

  final _name = TextEditingController();
  final _passport = TextEditingController();
  final _contact = TextEditingController();
  final _total = TextEditingController();
  final _paid = TextEditingController();

  final _name2 = TextEditingController();
  final _passport2 = TextEditingController();
  final _contact2 = TextEditingController();
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz);
  int? _toInt(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse('${v ?? ''}');
  }

  @override
  void initState() {
    super.initState();
    _loadInitial();
    _name.addListener(_onNameChanged);
    _total.addListener(() => setState(() {}));
    _paid.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _name.dispose();
    _passport.dispose();
    _contact.dispose();
    _total.dispose();
    _paid.dispose();
    _name2.dispose();
    _passport2.dispose();
    _contact2.dispose();
    super.dispose();
  }

  String _fmt(DateTime d) =>
      '${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}/${d.year}';
  String _apiDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  bool get _isDoubleBed => '${_selectedBed?['bed_type'] ?? ''}' == 'double';

  double get _remaining {
    final t = double.tryParse(_total.text.trim()) ?? 0;
    final p = double.tryParse(_paid.text.trim()) ?? 0;
    final r = t - p;
    return r > 0 ? r : 0;
  }

  Future<void> _loadInitial() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final result = await Future.wait([
        widget.api.getJson('/booking/rooms', query: {'branch_id': widget.api.branchId.toString()}),
        widget.api.getJson('/customers/', query: {'branch_id': widget.api.branchId.toString()}),
      ]);
      final rooms = (result[0] as List).cast<dynamic>();
      final customers = (result[1] as List).cast<dynamic>();
      setState(() {
        _rooms = rooms;
        _customers = customers;
        _roomId = rooms.isNotEmpty ? _toInt(rooms.first['id']) : null;
      });
      await _loadAvailableBeds();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadAvailableBeds() async {
    if (_roomId == null) {
      setState(() => _availableBeds = []);
      return;
    }
    final checkinDay = DateUtils.dateOnly(_checkin);
    final checkoutDay = DateUtils.dateOnly(_checkout);
    final sameDay = checkoutDay.isAtSameMomentAs(checkinDay);
    final sameDayAllowed = _isHourlyBooking && sameDay;
    if ((!checkoutDay.isAfter(checkinDay)) && !sameDayAllowed) {
      setState(() {
        _dateError = _t('Неверные даты', 'Noto‘g‘ri sanalar');
        _availableBeds = [];
        _selectedBed = null;
        _secondGuestEnabled = false;
      });
      return;
    }
    setState(() => _dateError = null);
    try {
      final rows = await widget.api.getJson('/booking/available-beds', query: {
        'branch_id': widget.api.branchId.toString(),
        'room_id': _roomId.toString(),
        'checkin': _apiDate(_checkin),
        'checkout': _apiDate(_checkout),
        'is_hourly': _isHourlyBooking ? 'true' : 'false',
      });
      final beds = (rows as List).cast<dynamic>();
      setState(() {
        _availableBeds = beds;
        if (_selectedBed != null &&
            !beds.any((b) => _toInt(b['id']) == _toInt(_selectedBed!['id']))) {
          _selectedBed = null;
          _secondGuestEnabled = false;
        }
      });
    } catch (e) {
      setState(() {
        _availableBeds = [];
        _dateError = friendlyErrorText(e.toString());
      });
    }
  }

  void _onNameChanged() {
    final q = _name.text.trim().toLowerCase();
    if (q.isEmpty) {
      setState(() => _customerSuggestions = []);
      return;
    }
    final filtered = _customers.where((c) {
      final n = '${c['name'] ?? ''}'.toLowerCase();
      final p = '${c['passport_id'] ?? ''}'.toLowerCase();
      final ct = '${c['contact'] ?? ''}'.toLowerCase();
      return n.contains(q) || p.contains(q) || ct.contains(q);
    }).take(8).toList();
    setState(() => _customerSuggestions = filtered);
  }

  void _selectCustomer(Map<String, dynamic> c) {
    setState(() {
      _name.text = '${c['name'] ?? ''}';
      _passport.text = '${c['passport_id'] ?? ''}';
      _contact.text = '${c['contact'] ?? ''}';
      _customerSuggestions = [];
    });
  }

  Future<void> _pickDate({required bool checkin, bool notify = false}) async {
    final initial = notify ? _notifyDate : (checkin ? _checkin : _checkout);
    final d = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (d == null) return;
    setState(() {
      if (notify) {
        _notifyDate = d;
      } else if (checkin) {
        _checkin = d;
      } else {
        _checkout = d;
        _notifyDate = d;
      }
    });
    await _loadAvailableBeds();
  }

  String _bedIcon(String t) {
    switch (t) {
      case 'double':
        return '👥';
      case 'child':
        return '🧸';
      default:
        return '👤';
    }
  }

  dynamic get _selectedRoomRow {
    if (_roomId == null) return null;
    for (final r in _rooms) {
      if (_toInt(r['id']) == _roomId) return r;
    }
    return null;
  }

  String get _selectedRoomBookingModeLabel {
    final room = _selectedRoomRow;
    final raw = '${room == null ? '' : (room['booking_mode'] ?? '')}'.trim().toLowerCase();
    return raw == 'full' ? _t('Полная комната', 'To‘liq xona') : _t('По кроватям', 'Kravat bo‘yicha');
  }

  Future<void> _submit() async {
    if (_selectedBed == null) {
      _snack(_t('Сначала выберите кровать', 'Avval krovat tanlang'));
      return;
    }
    if (_name.text.trim().isEmpty || _passport.text.trim().isEmpty || _contact.text.trim().isEmpty) {
      _snack(_t('Введите данные клиента', 'Mijoz ma’lumotlarini kiriting'));
      return;
    }
    final total = double.tryParse(_total.text.trim());
    if (total == null || total <= 0) {
      _snack(_t('Неверная общая сумма', 'Jami summa noto‘g‘ri'));
      return;
    }
    final paid = double.tryParse(_paid.text.trim()) ?? 0;

    Map<String, dynamic>? secondGuest;
    if (_isDoubleBed && _secondGuestEnabled) {
      if (_name2.text.trim().isEmpty || _passport2.text.trim().isEmpty || _contact2.text.trim().isEmpty) {
        _snack(_t('Данные второго гостя заполнены не полностью', 'Ikkinchi mehmon ma’lumotlari to‘liq emas'));
        return;
      }
      secondGuest = {
        'name': _name2.text.trim(),
        'passport_id': _passport2.text.trim(),
        'contact': _contact2.text.trim(),
      };
    }

    setState(() => _saving = true);
    try {
      final bedId = _toInt(_selectedBed!['id']);
      if (bedId == null) {
        _snack(_t('Неверный ID кровати', 'Krovat ID noto‘g‘ri'));
        return;
      }
      await widget.api.postJson('/booking/', {
        'branch_id': widget.api.branchId,
        'name': _name.text.trim(),
        'passport_id': _passport.text.trim(),
        'contact': _contact.text.trim(),
        'second_guest': secondGuest,
        'room_id': _roomId,
        'bed_id': bedId,
        'total': total,
        'paid': paid,
        'checkin': _apiDate(_checkin),
        'checkout': _apiDate(_checkout),
        'notify_date': _apiDate(_notifyDate),
        'is_hourly': _isHourlyBooking,
      });
      _snack(_t('Бронирование создано', 'Buyurtma yaratildi'));
      setState(() {
        _selectedBed = null;
        _secondGuestEnabled = false;
        _name.clear();
        _passport.clear();
        _contact.clear();
        _name2.clear();
        _passport2.clear();
        _contact2.clear();
        _total.clear();
        _paid.clear();
        _isHourlyBooking = false;
      });
      await _loadAvailableBeds();
      widget.onDataChanged();
    } catch (e) {
      _snack('$e');
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  void _snack(String msg) {
    showAppAlert(context, msg, error: msg.toLowerCase().contains('status'));
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return RefreshIndicator(
        onRefresh: _loadInitial,
        child: ListView(
          physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
          children: [
            const SizedBox(height: 140),
            _ErrorText(error: _error!),
            const SizedBox(height: 10),
            Center(
              child: Text(
                _t('Потяните вниз, чтобы обновить', 'Yangilash uchun pastga torting'),
                style: const TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadInitial,
      child: ListView(
        physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
        padding: const EdgeInsets.all(16),
        children: [
        Row(
          children: [
            Expanded(child: _SectionTitle('📝 ${_t("Новое бронирование", "Yangi bron")}')),
            IconButton(
              onPressed: _openBookingHistory,
              icon: const Icon(Icons.history, color: Color(0xFFCC9A4D)),
            )
          ],
        ),
        const SizedBox(height: 8),
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_t('Комната', 'Xona'), style: const TextStyle(fontSize: 16, color: Colors.black54)),
              const SizedBox(height: 8),
              DropdownButtonFormField<int>(
                value: _roomId,
                decoration: const InputDecoration(border: OutlineInputBorder()),
                items: _rooms
                    .map((r) {
                      final rid = _toInt(r['id']);
                      if (rid == null) return null;
                      return DropdownMenuItem<int>(
                        value: rid,
                        child: Text('${r['room_name'] ?? r['room_number']}'),
                      );
                    })
                    .whereType<DropdownMenuItem<int>>()
                    .toList(),
                onChanged: (v) async {
                  setState(() {
                    _roomId = v;
                    _selectedBed = null;
                    _secondGuestEnabled = false;
                  });
                  await _loadAvailableBeds();
                },
              ),
              const SizedBox(height: 10),
              Align(
                alignment: Alignment.centerLeft,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFE9F0FF),
                    borderRadius: BorderRadius.circular(999),
                    border: Border.all(color: const Color(0xFFCFDAF8)),
                  ),
                  child: Text(
                    '${_t("Режим брони", "Bron rejimi")}: $_selectedRoomBookingModeLabel',
                    style: const TextStyle(
                      color: Color(0xFF1D4ED8),
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(child: _DateField(label: _t('Заезд', 'Kirish'), value: _fmt(_checkin), onTap: () => _pickDate(checkin: true))),
                  const SizedBox(width: 10),
                  Expanded(child: _DateField(label: _t('Выезд', 'Chiqish'), value: _fmt(_checkout), onTap: () => _pickDate(checkin: false))),
                ],
              ),
              const SizedBox(height: 8),
              _DateField(label: '🔔 ${_t("Дата напоминания", "Eslatma sanasi")}', value: _fmt(_notifyDate), onTap: () => _pickDate(checkin: false, notify: true)),
              const SizedBox(height: 4),
              Text(_t('Дата отправки напоминания об оплате', "To'lov bo'yicha eslatma yuboriladigan sana"), style: const TextStyle(fontSize: 12, color: Colors.black45)),
              const SizedBox(height: 6),
              CheckboxListTile(
                value: _isHourlyBooking,
                dense: true,
                contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(_t('Почасовое бронирование', 'Soatlik bron')),
                subtitle: Text(_t('Отмечайте, если бронь почасовая', "Bron soatlik bo'lsa belgilang"), style: const TextStyle(fontSize: 12)),
                onChanged: (v) async {
                  setState(() => _isHourlyBooking = v ?? false);
                  await _loadAvailableBeds();
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_t('Доступные кровати на выбранное время', "Mavjud kravatlar tanlangan vaqt bo'yicha"), style: const TextStyle(fontSize: 16, color: Colors.black54)),
              const SizedBox(height: 10),
              if (_dateError != null) Text(_dateError!, style: const TextStyle(color: Colors.red, fontWeight: FontWeight.w600)),
              if (_dateError == null && _availableBeds.isEmpty) Text(_t('Свободные кровати не найдены', "Bo'sh krovat topilmadi")),
              if (_availableBeds.isNotEmpty)
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: _availableBeds.map((b) {
                    final bed = Map<String, dynamic>.from(b as Map);
                    final selected = _selectedBed != null &&
                        (bed['id'] as num).toInt() == (_selectedBed!['id'] as num).toInt();
                    final t = '${bed['bed_type'] ?? 'single'}';
                    return ChoiceChip(
                      label: Text('${_bedIcon(t)} ${_t("Кровать", "Kravat")} ${bed['bed_number']}'),
                      selected: selected,
                      onSelected: (_) {
                        setState(() {
                          _selectedBed = bed;
                          if (t != 'double') _secondGuestEnabled = false;
                        });
                      },
                    );
                  }).toList(),
                ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        _Card(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(_t('Имя клиента', 'Mijoz ismi'), style: const TextStyle(fontSize: 16, color: Colors.black54)),
              const SizedBox(height: 8),
              TextField(
                controller: _name,
                decoration: InputDecoration(
                  hintText: _t('Выберите клиента из списка или введите нового', "Mijozni ro'yxatdan tanlang yoki yangi mijoz"),
                  border: const OutlineInputBorder(),
                ),
              ),
              if (_customerSuggestions.isNotEmpty)
                Container(
                  margin: const EdgeInsets.only(top: 6),
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFD1D5DB)),
                    color: Colors.white,
                  ),
                  child: Column(
                    children: _customerSuggestions.map((c) {
                      final m = Map<String, dynamic>.from(c as Map);
                      return ListTile(
                        dense: true,
                        title: Text('${m['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                        subtitle: Text('🪪 ${m['passport_id'] ?? ''} • 📞 ${m['contact'] ?? ''}'),
                        onTap: () => _selectCustomer(m),
                      );
                    }).toList(),
                  ),
                ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _passport,
                      decoration: InputDecoration(labelText: _t('Паспорт ID', 'Passport ID'), border: const OutlineInputBorder()),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: TextField(
                      controller: _contact,
                      decoration: InputDecoration(labelText: _t('Контакт', 'Telefon'), border: const OutlineInputBorder()),
                    ),
                  ),
                ],
              ),
              if (_isDoubleBed) ...[
                const SizedBox(height: 8),
                CheckboxListTile(
                  contentPadding: EdgeInsets.zero,
                  value: _secondGuestEnabled,
                  onChanged: (v) => setState(() => _secondGuestEnabled = v == true),
                  title: Text(_t('Второй гость (необязательно)', 'Ikkinchi mehmon (ixtiyoriy)')),
                  controlAffinity: ListTileControlAffinity.leading,
                ),
              ],
              if (_isDoubleBed && _secondGuestEnabled) ...[
                const Divider(),
                TextField(
                  controller: _name2,
                  decoration: InputDecoration(labelText: _t('Имя клиента (2)', 'Mijoz ismi (2)'), border: const OutlineInputBorder()),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: TextField(
                        controller: _passport2,
                        decoration: InputDecoration(labelText: _t('Паспорт ID (2)', 'Passport ID (2)'), border: const OutlineInputBorder()),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TextField(
                        controller: _contact2,
                        decoration: InputDecoration(labelText: _t('Контакт (2)', 'Telefon (2)'), border: const OutlineInputBorder()),
                      ),
                    ),
                  ],
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 12),
        _Card(
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _total,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(labelText: _t('Общая сумма', 'Jami miqdor'), border: const OutlineInputBorder()),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _paid,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(labelText: _t('Оплаченная сумма', "To'langan miqdor"), border: const OutlineInputBorder()),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 12),
        Text("${_t('Оставшаяся сумма', 'Qolgan summa')}: ${_remaining.toStringAsFixed(2)}", style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        const SizedBox(height: 10),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: const Color(0xFF3D8BDF),
              padding: const EdgeInsets.symmetric(vertical: 14),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            ),
            onPressed: _saving ? null : _submit,
            child: _saving
                ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                : Text('✅ ${_t("Подтвердить бронирование", "Buyurtmani tasdiqlash")}', style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
        ),
        ],
      ),
    );
  }

  Future<void> _openBookingHistory() async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (_) => _BookingHistorySheet(api: widget.api),
    );
  }
}

class _DateField extends StatelessWidget {
  const _DateField({required this.label, required this.value, required this.onTap});
  final String label;
  final String value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontSize: 14, color: Colors.black54)),
        const SizedBox(height: 4),
        InkWell(
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
            decoration: BoxDecoration(
              border: Border.all(color: const Color(0xFFD1D5DB)),
              borderRadius: BorderRadius.circular(10),
              color: Colors.white,
            ),
            child: Row(
              children: [
                Expanded(child: Text(value, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600))),
                const Icon(Icons.calendar_month, size: 18),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

class _BookingHistorySheet extends StatefulWidget {
  const _BookingHistorySheet({required this.api});
  final _ApiClient api;

  @override
  State<_BookingHistorySheet> createState() => _BookingHistorySheetState();
}

class _BookingHistorySheetState extends State<_BookingHistorySheet> {
  DateTime _from = DateTime.now().subtract(const Duration(days: 30));
  DateTime _to = DateTime.now();
  final _search = TextEditingController();
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  String _apiDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  String _fmtInput(DateTime d) =>
      '${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}/${d.year}';
  String _fmtOut(String v) {
    final d = DateTime.tryParse(v);
    if (d == null) return v;
    return '${d.day.toString().padLeft(2, '0')}/${d.month.toString().padLeft(2, '0')}/${d.year}';
  }

  Future<void> _pick(bool from) async {
    final initial = from ? _from : _to;
    final p = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (p == null) return;
    setState(() {
      if (from) {
        _from = p;
      } else {
        _to = p;
      }
    });
  }

  Future<void> _load() async {
    if (_from.isAfter(_to)) {
      setState(() => _error = 'From date must be before To date');
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/booking-history/', query: {
        'branch_id': widget.api.branchId.toString(),
        'from_date': _apiDate(_from),
        'to_date': _apiDate(_to),
      });
      setState(() => _rows = (data as List).cast<dynamic>());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = _search.text.trim().toLowerCase();
    final filtered = _rows.where((r) {
      final n = '${r['customer_name'] ?? ''}'.toLowerCase();
      final p = '${r['passport_id'] ?? ''}'.toLowerCase();
      return q.isEmpty || n.contains(q) || p.contains(q);
    }).toList();

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 12,
          right: 12,
          top: 12,
          bottom: MediaQuery.of(context).viewInsets.bottom + 10,
        ),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.8,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Text('📜 История бронирований', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
              Row(
                children: [
                  Expanded(
                    child: _DateField(label: '', value: _fmtInput(_from), onTap: () => _pick(true)),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _DateField(label: '', value: _fmtInput(_to), onTap: () => _pick(false)),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _search,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: trPair(ru: 'Поиск клиента / паспорта', uz: 'Mijoz / passport qidirish'),
                        border: const OutlineInputBorder(),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _load,
                    style: FilledButton.styleFrom(
                      backgroundColor: const Color(0xFF3D8BDF),
                      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                    ),
                    child: Text(trPair(ru: 'поиск', uz: 'izlash')),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              if (_loading) const Expanded(child: Center(child: CircularProgressIndicator())),
              if (_error != null && !_loading)
                Expanded(
                  child: Center(
                    child: Text(_error!, style: const TextStyle(color: Colors.red)),
                  ),
                ),
              if (!_loading && _error == null)
                Expanded(
                  child: filtered.isEmpty
                      ? Center(child: Text(trPair(ru: 'Бронирований не найдено', uz: 'Buyurtmalar topilmadi')))
                      : ListView.separated(
                          itemCount: filtered.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 10),
                          itemBuilder: (context, i) {
                            final r = filtered[i] as Map<String, dynamic>;
                            return Container(
                              padding: const EdgeInsets.all(12),
                              decoration: BoxDecoration(
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: const Color(0xFFE5E7EB)),
                              ),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('👤 ${r['customer_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                                  const SizedBox(height: 2),
                                  Text('🪪 ${r['passport_id'] ?? ''}', style: const TextStyle(color: Colors.black54)),
                                  Text('🏠 ${r['room_name'] ?? r['room_number'] ?? ''} • 🛏 Kravat ${r['bed_number'] ?? ''}',
                                      style: const TextStyle(color: Colors.black54)),
                                  Text('🗓 ${_fmtOut('${r['checkin_date'] ?? ''}')} → ${_fmtOut('${r['checkout_date'] ?? ''}')}',
                                      style: const TextStyle(color: Colors.black54)),
                                  const SizedBox(height: 6),
                                  Align(
                                    alignment: Alignment.centerRight,
                                    child: Text(
                                      '💰 ${r['total_amount'] ?? 0}',
                                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 20),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PaymentsPage extends StatefulWidget {
  const _PaymentsPage({required this.api});
  final _ApiClient api;

  @override
  State<_PaymentsPage> createState() => _PaymentsPageState();
}

class _PaymentsPageState extends State<_PaymentsPage> {
  late int _month;
  late int _year;
  bool _loading = true;
  String? _error;
  Map<String, dynamic> _finance = {};
  final _titleCtrl = TextEditingController();
  final _amountCtrl = TextEditingController();
  bool _addingExpense = false;
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz);

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _month = now.month;
    _year = now.year;
    _loadFinance();
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _amountCtrl.dispose();
    super.dispose();
  }

  String _fmtNum(dynamic x) {
    final n = (x is num) ? x : num.tryParse('$x') ?? 0;
    return n.toStringAsFixed(0).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ' ');
  }

  Future<void> _loadFinance() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final d = await widget.api.getJson('/payments/monthly-finance', query: {
        'branch_id': widget.api.branchId.toString(),
        'year': _year.toString(),
        'month': _month.toString(),
      });
      setState(() => _finance = Map<String, dynamic>.from(d as Map));
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _addExpense() async {
    final title = _titleCtrl.text.trim();
    final amount = double.tryParse(_amountCtrl.text.trim());
    if (title.isEmpty || amount == null || amount <= 0) {
      showAppAlert(context, _t('Введите корректно заголовок и сумму', "Sarlavha va summa to'g'ri kiriting"), error: true);
      return;
    }
    setState(() => _addingExpense = true);
    try {
      final now = DateTime.now();
      final date = '${now.year}-${now.month.toString().padLeft(2, '0')}-${now.day.toString().padLeft(2, '0')}';
      await widget.api.postJson('/payments/expense', {
        'branch_id': widget.api.branchId,
        'title': title,
        'category': 'other',
        'amount': amount,
        'expense_date': date,
      });
      _titleCtrl.clear();
      _amountCtrl.clear();
      await _loadFinance();
      if (!mounted) return;
      showAppAlert(context, _t('Расход добавлен', "Xarajat qo'shildi"));
    } catch (e) {
      showAppAlert(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => _addingExpense = false);
    }
  }

  Future<void> _openSimpleListSheet({
    required String title,
    required Future<dynamic> Function() loader,
    required Widget Function(Map<String, dynamic>) itemBuilder,
  }) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => FutureBuilder<dynamic>(
        future: loader(),
        builder: (context, snap) {
          return SafeArea(
            child: SizedBox(
              height: MediaQuery.of(context).size.height * 0.78,
              child: Column(
                children: [
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 10, 6, 4),
                    child: Row(
                      children: [
                        Text(title, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                        const Spacer(),
                        IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                      ],
                    ),
                  ),
                  Expanded(
                    child: () {
                      if (snap.connectionState != ConnectionState.done) {
                        return const Center(child: CircularProgressIndicator());
                      }
                      if (snap.hasError) {
                        return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.red)));
                      }
                      final rows = (snap.data as List).cast<dynamic>();
                      if (rows.isEmpty) return const Center(child: Text('Ma’lumot yo‘q'));
                      return ListView.separated(
                        padding: const EdgeInsets.all(12),
                        itemCount: rows.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => itemBuilder(Map<String, dynamic>.from(rows[i] as Map)),
                      );
                    }(),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  DateTime _firstDay() => DateTime(_year, _month, 1);
  DateTime _lastDay() => DateTime(_year, _month + 1, 0);
  String _apiDate(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    final income = _fmtNum(_finance['income'] ?? 0);
    final expenses = _fmtNum(_finance['expenses'] ?? 0);
    final debt = _fmtNum(_finance['debt'] ?? 0);
    final refunds = _fmtNum(_finance['refunds'] ?? 0);
    final profit = _fmtNum((_finance['income'] ?? 0) - (_finance['expenses'] ?? 0) - (_finance['refunds'] ?? 0));

    return RefreshIndicator(
      onRefresh: _loadFinance,
      child: ListView(
        physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
        padding: const EdgeInsets.all(16),
        children: [
        _SectionTitle('💰 ${_t("Ежемесячные финансы", "Oylik moliya")}'),
        const SizedBox(height: 10),
        _Card(
          child: Row(
            children: [
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: _month,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  ),
                  items: List.generate(12, (i) => i + 1)
                      .map((m) => DropdownMenuItem(value: m, child: Text('$m')))
                      .toList(),
                  onChanged: (v) => setState(() => _month = v ?? _month),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: _year,
                  decoration: const InputDecoration(
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                  ),
                  items: List.generate(11, (i) => DateTime.now().year - 5 + i)
                      .map((y) => DropdownMenuItem(value: y, child: Text('$y')))
                      .toList(),
                  onChanged: (v) => setState(() => _year = v ?? _year),
                ),
              ),
              const SizedBox(width: 10),
              FilledButton(
                onPressed: _loadFinance,
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFF3D8BDF), padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
                child: Text(_t('поиск', 'izlash')),
              )
            ],
          ),
        ),
        const SizedBox(height: 12),
        if (_loading) const Center(child: Padding(padding: EdgeInsets.all(12), child: CircularProgressIndicator())),
        if (_error != null && !_loading) _ErrorText(error: _error!),
        if (!_loading && _error == null) ...[
          Row(
            children: [
              Expanded(child: _NumberBox(title: _t('Доход', 'Daromad'), value: income, bg: const Color(0xFFD1FAE5))),
              const SizedBox(width: 10),
              Expanded(child: _NumberBox(title: _t('Расходы', 'Xarajatlar'), value: expenses, bg: const Color(0xFFFEE2E2))),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(child: _NumberBox(title: _t('Долг', 'Qarz'), value: debt, bg: const Color(0xFFFEF9C3))),
              const SizedBox(width: 10),
              Expanded(child: _NumberBox(title: _t('Возвраты', 'Qaytarilgan pullar'), value: refunds, bg: const Color(0xFFDBEAFE))),
            ],
          ),
          const SizedBox(height: 10),
          _Card(
            child: Column(
              children: [
                Text(_t('Чистая прибыль', 'Sof foyda'), style: const TextStyle(fontSize: 15, color: Colors.black54)),
                const SizedBox(height: 4),
                Text(profit, style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w800)),
              ],
            ),
          ),
          const SizedBox(height: 12),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('➕ ${_t("Добавить дополнительный расход", "Qo\'shimcha xarajat qo\'shish")}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                const SizedBox(height: 10),
                TextField(
                  controller: _titleCtrl,
                  decoration: InputDecoration(hintText: _t('Заголовок', 'Sarlavha'), border: const OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                TextField(
                  controller: _amountCtrl,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(hintText: _t('Сумма', 'Miqdor'), border: const OutlineInputBorder()),
                ),
                const SizedBox(height: 10),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
                    onPressed: _addingExpense ? null : _addExpense,
                    child: _addingExpense
                        ? const SizedBox(height: 18, width: 18, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_t('Добавить', "Qo'shish")),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Wrap(
            alignment: WrapAlignment.center,
            runAlignment: WrapAlignment.center,
            spacing: 10,
            runSpacing: 10,
            children: [
              _ActionTile(
                emoji: '📜',
                label: _t('История\nплатежей', "To'lovlar\ntarixi"),
                onTap: () => showModalBottomSheet(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                  ),
                  builder: (_) => _PaymentHistorySheet(
                    api: widget.api,
                    initialYear: _year,
                    initialMonth: _month,
                  ),
                ),
              ),
              _ActionTile(
                emoji: '💸',
                label: _t('История\nрасходов', "Xarajatlar\ntarixi"),
                onTap: () => showModalBottomSheet(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                  ),
                  builder: (_) => _ExpenseHistorySheet(
                    api: widget.api,
                    initialYear: _year,
                    initialMonth: _month,
                  ),
                ),
              ),
              _ActionTile(
                emoji: '💳',
                label: _t('История долгов', 'Qarzlar tarixi'),
                onTap: () => showModalBottomSheet(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                  ),
                  builder: (_) => _DebtAnalyticsSheet(
                    api: widget.api,
                  ),
                ),
              ),
              _ActionTile(
                emoji: '👤',
                label: _t('Клиенты', 'Mijozlar'),
                onTap: () => showModalBottomSheet(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                  ),
                  builder: (_) => _CustomersSheet(api: widget.api),
                ),
              ),
              _ActionTile(
                emoji: '↩️',
                label: _t('Возвраты', 'Qaytarilgan pullar'),
                onTap: () => showModalBottomSheet(
                  context: context,
                  isScrollControlled: true,
                  backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(
                    borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                  ),
                  builder: (_) => _RefundsSheet(
                    api: widget.api,
                    initialYear: _year,
                    initialMonth: _month,
                  ),
                ),
              ),
            ],
          ),
        ],
        ],
      ),
    );
  }
}

class _ActionTile extends StatelessWidget {
  const _ActionTile({required this.emoji, required this.label, required this.onTap});
  final String emoji;
  final String label;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        width: 155,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 22),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          border: Border.all(color: const Color(0xFFE5E7EB)),
        ),
        child: Column(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 24)),
            const SizedBox(height: 8),
            Text(label, textAlign: TextAlign.center, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
          ],
        ),
      ),
    );
  }
}

class _HistoryTile extends StatelessWidget {
  const _HistoryTile({required this.title, required this.subtitle, required this.amount});
  final String title;
  final String subtitle;
  final String amount;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(subtitle, style: const TextStyle(color: Colors.black54)),
              ],
            ),
          ),
          if (amount.trim().isNotEmpty)
            Text(
              amount,
              style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
        ],
      ),
    );
  }
}

class _PaymentHistorySheet extends StatefulWidget {
  const _PaymentHistorySheet({
    required this.api,
    required this.initialYear,
    required this.initialMonth,
  });

  final _ApiClient api;
  final int initialYear;
  final int initialMonth;

  @override
  State<_PaymentHistorySheet> createState() => _PaymentHistorySheetState();
}

class _PaymentHistorySheetState extends State<_PaymentHistorySheet> {
  late int _year = widget.initialYear;
  late int _month = widget.initialMonth;
  String _roomFilter = '';
  final _search = TextEditingController();
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  String _fmtAmount(dynamic x) {
    final n = (x is num) ? x : num.tryParse('$x') ?? 0;
    return n.toStringAsFixed(0).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ' ');
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/payment-history/', query: {
        'branch_id': widget.api.branchId.toString(),
        'year': _year.toString(),
        'month': _month.toString(),
      });
      setState(() => _rows = (data as List).cast<dynamic>());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    String roomOf(Map<String, dynamic> r) => '${r['room_name'] ?? r['room_number'] ?? ''}'.trim();
    final roomOptions = _rows
        .map((e) => roomOf(Map<String, dynamic>.from(e as Map)))
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    final q = _search.text.trim().toLowerCase();
    final filtered = _rows.where((r) {
      final m = Map<String, dynamic>.from(r as Map);
      final name = '${m['customer_name'] ?? ''}'.toLowerCase();
      final pass = '${m['passport_id'] ?? ''}'.toLowerCase();
      final room = roomOf(m);
      final roomOk = _roomFilter.isEmpty || room == _roomFilter;
      final textOk = q.isEmpty || name.contains(q) || pass.contains(q);
      return roomOk && textOk;
    }).toList();

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          8,
          10,
          8,
          MediaQuery.of(context).viewInsets.bottom + 8,
        ),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.82,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 6),
                child: Row(
                  children: [
                    Text('📜 ${_t('История платежей', "To'lovlar tarixi")}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              _Card(
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<int>(
                            value: _month,
                            decoration: const InputDecoration(
                              border: OutlineInputBorder(),
                              isDense: true,
                              contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                            ),
                            items: List.generate(12, (i) => i + 1)
                                .map((m) => DropdownMenuItem(value: m, child: Text('$m')))
                                .toList(),
                            onChanged: (v) => setState(() => _month = v ?? _month),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: DropdownButtonFormField<int>(
                            value: _year,
                            decoration: const InputDecoration(
                              border: OutlineInputBorder(),
                              isDense: true,
                              contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                            ),
                            items: List.generate(11, (i) => DateTime.now().year - 5 + i)
                                .map((y) => DropdownMenuItem(value: y, child: Text('$y')))
                                .toList(),
                            onChanged: (v) => setState(() => _year = v ?? _year),
                          ),
                        ),
                        const SizedBox(width: 8),
                        FilledButton(
                          onPressed: _load,
                          style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF3D8BDF),
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          ),
                          child: Text(_t('Загрузить', 'Yuklash')),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                    TextField(
                      controller: _search,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: _t('Поиск клиента / паспорта', 'Mijoz / passport qidirish'),
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: _roomFilter.isEmpty ? '' : _roomFilter,
                      decoration: InputDecoration(
                        labelText: _t('Комната', 'Xona'),
                        border: const OutlineInputBorder(),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      items: [
                        DropdownMenuItem(value: '', child: Text(_t('Все комнаты', 'Barcha xonalar'))),
                        ...roomOptions.map((r) => DropdownMenuItem(value: r, child: Text(r))),
                      ],
                      onChanged: (v) => setState(() => _roomFilter = v ?? ''),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: () {
                  if (_loading) return const Center(child: CircularProgressIndicator());
                  if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
                  if (filtered.isEmpty) return Center(child: Text(_t('Платежей нет', "To'lovlar yo'q")));
                  return ListView.separated(
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (_, i) {
                      final r = Map<String, dynamic>.from(filtered[i] as Map);
                      return _Card(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text('${r['payment_date'] ?? r['created_at'] ?? ''}', style: const TextStyle(color: Color(0xFF64748B))),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Expanded(
                                  child: Text('${r['customer_name'] ?? ''}',
                                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                                ),
                                Text(
                                  _fmtAmount(r['amount'] ?? r['paid_amount'] ?? 0),
                                  style: const TextStyle(color: Color(0xFF2E9F45), fontWeight: FontWeight.w700, fontSize: 22),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text('${r['passport_id'] ?? ''}', style: const TextStyle(color: Color(0xFF475467))),
                            const SizedBox(height: 4),
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    '🏠 ${r['room_name'] ?? r['room_number'] ?? ''} • 🛏 ${_t("Кровать", "Kravat")} ${r['bed_number'] ?? ''}',
                                    style: const TextStyle(color: Color(0xFF334155)),
                                  ),
                                ),
                                Text(_t('клиент', 'mijoz'), style: const TextStyle(color: Color(0xFF64748B))),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  );
                }(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExpenseHistorySheet extends StatefulWidget {
  const _ExpenseHistorySheet({
    required this.api,
    required this.initialYear,
    required this.initialMonth,
  });

  final _ApiClient api;
  final int initialYear;
  final int initialMonth;

  @override
  State<_ExpenseHistorySheet> createState() => _ExpenseHistorySheetState();
}

class _ExpenseHistorySheetState extends State<_ExpenseHistorySheet> {
  late int _year = widget.initialYear;
  late int _month = widget.initialMonth;
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _fmtAmount(dynamic x) {
    final n = (x is num) ? x : num.tryParse('$x') ?? 0;
    return n.toStringAsFixed(0).replaceAllMapped(RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ' ');
  }

  String _monthLabel(int m) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    if (m < 1 || m > 12) return '$m';
    return months[m - 1];
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/payments/expenses', query: {
        'branch_id': widget.api.branchId.toString(),
        'year': _year.toString(),
        'month': _month.toString(),
      });
      setState(() => _rows = (data as List).cast<dynamic>());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 8),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.72,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 6),
                child: Row(
                  children: [
                    Text('💸 ${_t('История расходов', 'Xarajatlar tarixi')}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      value: _month,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                      ),
                      items: List.generate(12, (i) => i + 1)
                          .map((m) => DropdownMenuItem(value: m, child: Text(_monthLabel(m))))
                          .toList(),
                      onChanged: (v) => setState(() => _month = v ?? _month),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      value: _year,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                      ),
                      items: List.generate(11, (i) => DateTime.now().year - 5 + i)
                          .map((y) => DropdownMenuItem(value: y, child: Text('$y')))
                          .toList(),
                      onChanged: (v) => setState(() => _year = v ?? _year),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _load,
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFF3D8BDF), padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
                    child: Text(_t('Поиск', 'Izlash')),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Expanded(
                child: () {
                  if (_loading) return const Center(child: CircularProgressIndicator());
                  if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
                  if (_rows.isEmpty) return Center(child: Text(_t('Расходов нет', "Xarajatlar yo'q")));
                  return ListView.separated(
                    itemCount: _rows.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final r = Map<String, dynamic>.from(_rows[i] as Map);
                      return _Card(
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${r['expense_date'] ?? ''}', style: const TextStyle(color: Color(0xFF64748B))),
                                  const SizedBox(height: 4),
                                  Text('${r['title'] ?? ''}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                                  Text('${r['category'] ?? ''}', style: const TextStyle(color: Color(0xFF64748B))),
                                ],
                              ),
                            ),
                            Text(
                              _fmtAmount(r['amount'] ?? 0),
                              style: const TextStyle(color: Color(0xFFC0392B), fontSize: 20, fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                      );
                    },
                  );
                }(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _DebtAnalyticsSheet extends StatefulWidget {
  const _DebtAnalyticsSheet({required this.api});
  final _ApiClient api;

  @override
  State<_DebtAnalyticsSheet> createState() => _DebtAnalyticsSheetState();
}

class _DebtAnalyticsSheetState extends State<_DebtAnalyticsSheet> {
  DateTime _from = DateTime(2025, 12, 31);
  DateTime _to = DateTime.now();
  String _roomFilter = '';
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];
  final _search = TextEditingController();
  final Map<int, TextEditingController> _payCtrls = {};
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    for (final c in _payCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  String _apiDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  String _fmt(DateTime d) =>
      '${d.month.toString().padLeft(2, '0')}/${d.day.toString().padLeft(2, '0')}/${d.year}';

  Future<void> _pick(bool from) async {
    final init = from ? _from : _to;
    final p = await showDatePicker(
      context: context,
      initialDate: init,
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (p == null) return;
    setState(() {
      if (from) {
        _from = p;
      } else {
        _to = p;
      }
    });
  }

  Future<void> _load() async {
    if (_from.isAfter(_to)) {
      setState(() => _error = _t('Неверный диапазон дат', "Noto'g'ri sana oralig'i"));
      return;
    }
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/debts/', query: {
        'branch_id': widget.api.branchId.toString(),
        'from_date': _apiDate(_from),
        'to_date': _apiDate(_to),
      });
      final rows = (data as List).cast<dynamic>();
      for (final r in rows) {
        final m = Map<String, dynamic>.from(r as Map);
        final bookingId = ((m['booking_id'] ?? m['id']) as num).toInt();
        _payCtrls.putIfAbsent(bookingId, () => TextEditingController());
      }
      setState(() => _rows = rows);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _payDebt(Map<String, dynamic> r) async {
    final bookingId = ((r['booking_id'] ?? r['id']) as num).toInt();
    final ctrl = _payCtrls[bookingId];
    final amount = double.tryParse(ctrl?.text.trim() ?? '');
    if (amount == null || amount <= 0) {
      showAppAlert(context, _t('Введите сумму платежа', "To'lov summasini kiriting"), error: true);
      return;
    }
    await widget.api.postJson('/debts/pay', {
      'branch_id': widget.api.branchId,
      'booking_id': bookingId,
      'amount': amount,
      'paid_by': 'customer',
    });
    ctrl?.clear();
    await _load();
    if (!mounted) return;
    showAppAlert(context, _t('Оплата успешно проведена', "To'lov muvaffaqiyatli qabul qilindi"));
  }

  @override
  Widget build(BuildContext context) {
    String roomOf(Map<String, dynamic> r) => '${r['room_name'] ?? r['room_number'] ?? ''}'.trim();
    final roomOptions = _rows
        .map((e) => roomOf(Map<String, dynamic>.from(e as Map)))
        .where((e) => e.isNotEmpty)
        .toSet()
        .toList()
      ..sort();
    final q = _search.text.trim().toLowerCase();
    final filtered = _rows.where((r) {
      final m = Map<String, dynamic>.from(r as Map);
      final n = '${m['customer_name'] ?? ''}'.toLowerCase();
      final p = '${m['passport_id'] ?? ''}'.toLowerCase();
      final room = roomOf(m);
      final roomOk = _roomFilter.isEmpty || room == _roomFilter;
      final textOk = q.isEmpty || n.contains(q) || p.contains(q);
      return roomOk && textOk;
    }).toList();

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(
          8,
          10,
          8,
          MediaQuery.of(context).viewInsets.bottom + 8,
        ),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.84,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 6),
                child: Row(
                  children: [
                    Text('💳 ${_t('Аналитика долгов', 'Qarzlar tahlili')}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              _Card(
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: InkWell(
                            onTap: () => _pick(true),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                              decoration: BoxDecoration(
                                border: Border.all(color: const Color(0xFFD1D5DB)),
                                borderRadius: BorderRadius.circular(10),
                                color: Colors.white,
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      _fmt(_from),
                                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                  const Icon(Icons.calendar_month, size: 18),
                                ],
                              ),
                            ),
                          ),
                        ),
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 8),
                          child: Text('—', style: TextStyle(fontSize: 20, color: Color(0xFF6B7280))),
                        ),
                        Expanded(
                          child: InkWell(
                            onTap: () => _pick(false),
                            borderRadius: BorderRadius.circular(10),
                            child: Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                              decoration: BoxDecoration(
                                border: Border.all(color: const Color(0xFFD1D5DB)),
                                borderRadius: BorderRadius.circular(10),
                                color: Colors.white,
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      _fmt(_to),
                                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600),
                                    ),
                                  ),
                                  const Icon(Icons.calendar_month, size: 18),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: FilledButton(
                        onPressed: _load,
                        style: FilledButton.styleFrom(
                          backgroundColor: const Color(0xFF3D8BDF),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                        ),
                        child: Text(_t('Подтвердить', 'Tasdiqlash')),
                      ),
                    ),
                    const SizedBox(height: 8),
                    TextField(
                      controller: _search,
                      onChanged: (_) => setState(() {}),
                      decoration: InputDecoration(
                        hintText: _t('Поиск клиента / паспорта', 'Mijoz / passport qidirish'),
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                    ),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: _roomFilter.isEmpty ? '' : _roomFilter,
                      decoration: InputDecoration(
                        labelText: _t('Комната', 'Xona'),
                        border: const OutlineInputBorder(),
                        isDense: true,
                        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      items: [
                        DropdownMenuItem(value: '', child: Text(_t('Все комнаты', 'Barcha xonalar'))),
                        ...roomOptions.map((r) => DropdownMenuItem(value: r, child: Text(r))),
                      ],
                      onChanged: (v) => setState(() => _roomFilter = v ?? ''),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: () {
                  if (_loading) return const Center(child: CircularProgressIndicator());
                  if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
                  if (filtered.isEmpty) return Center(child: Text(_t('Долгов нет', "Qarzlar yo'q")));
                  return ListView.separated(
                    keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
                    padding: const EdgeInsets.only(bottom: 16),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final r = Map<String, dynamic>.from(filtered[i] as Map);
                      final bookingId = ((r['booking_id'] ?? r['id']) as num).toInt();
                      final ctrl = _payCtrls.putIfAbsent(bookingId, () => TextEditingController());
                      return _Card(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text('${r['customer_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18)),
                                ),
                                Text(
                                  '${r['debt_amount'] ?? r['remaining_amount'] ?? 0}',
                                  style: const TextStyle(color: Color(0xFFC0392B), fontSize: 22, fontWeight: FontWeight.w700),
                                ),
                              ],
                            ),
                            const SizedBox(height: 2),
                            Text('${r['passport_id'] ?? ''}', style: const TextStyle(color: Color(0xFF64748B))),
                            Text('🏠 ${r['room_name'] ?? r['room_number'] ?? ''} • 🛏 ${_t("Кровать", "Kravat")} ${r['bed_number'] ?? ''}',
                                style: const TextStyle(color: Color(0xFF475467))),
                            Text('${r['checkin_date'] ?? ''} → ${r['checkout_date'] ?? ''}',
                                style: const TextStyle(color: Color(0xFF64748B))),
                            const SizedBox(height: 8),
                            TextField(
                              controller: ctrl,
                              keyboardType: const TextInputType.numberWithOptions(decimal: true),
                              decoration: InputDecoration(
                                hintText: _t('Сумма платежа', "To'lov summasi"),
                                border: OutlineInputBorder(),
                              ),
                            ),
                            const SizedBox(height: 8),
                            SizedBox(
                              width: double.infinity,
                              child: FilledButton(
                                style: FilledButton.styleFrom(backgroundColor: const Color(0xFF57C568)),
                                onPressed: () => _payDebt(r),
                                child: Text(_t('Оплатить', "To'lash")),
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  );
                }(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CustomersSheet extends StatefulWidget {
  const _CustomersSheet({required this.api});
  final _ApiClient api;

  @override
  State<_CustomersSheet> createState() => _CustomersSheetState();
}

class _CustomersSheetState extends State<_CustomersSheet> {
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];
  final _search = TextEditingController();
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/customers/', query: {
        'branch_id': widget.api.branchId.toString(),
      });
      setState(() => _rows = (data as List).cast<dynamic>());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _editCustomer(Map<String, dynamic> c) async {
    final name = TextEditingController(text: '${c['name'] ?? ''}');
    final pass = TextEditingController(text: '${c['passport_id'] ?? ''}');
    final phone = TextEditingController(text: '${c['contact'] ?? ''}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t('Редактировать', 'Tahrirlash')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(controller: name, decoration: InputDecoration(labelText: _t('Имя', 'Ism'), border: const OutlineInputBorder())),
            const SizedBox(height: 8),
            TextField(controller: pass, decoration: InputDecoration(labelText: _t('Паспорт', 'Passport'), border: const OutlineInputBorder())),
            const SizedBox(height: 8),
            TextField(controller: phone, decoration: InputDecoration(labelText: _t('Телефон', 'Telefon'), border: const OutlineInputBorder())),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Отмена', 'Bekor qilish'))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Сохранить', 'Saqlash'))),
        ],
      ),
    );
    if (ok != true) return;
    await widget.api.putQuery('/customers/${c['id']}', {
      'name': name.text.trim(),
      'passport_id': pass.text.trim(),
      'contact': phone.text.trim(),
    });
    await _load();
  }

  Future<void> _deleteCustomer(Map<String, dynamic> c) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(_t('Удалить клиента', "Mijozni o'chirish")),
        content: Text('${_t('Удалить', "O'chirish")} ${c['name'] ?? ''}?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_t('Нет', "Yo'q"))),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_t('Да', 'Ha'))),
        ],
      ),
    );
    if (ok != true) return;
    await widget.api.deleteJson('/customers/${c['id']}');
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final q = _search.text.trim().toLowerCase();
    final filtered = _rows.where((r) {
      final m = Map<String, dynamic>.from(r as Map);
      return q.isEmpty ||
          '${m['name'] ?? ''}'.toLowerCase().contains(q) ||
          '${m['passport_id'] ?? ''}'.toLowerCase().contains(q) ||
          '${m['contact'] ?? ''}'.toLowerCase().contains(q);
    }).toList();

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 8),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.82,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 6),
                child: Row(
                  children: [
                    Text('👤 ${_t('Клиенты', 'Mijozlar')}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              _Card(
                child: TextField(
                  controller: _search,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: _t('Поиск по имени, паспорту или телефону', 'Ism, passport yoki telefon bo\'yicha qidirish'),
                    border: OutlineInputBorder(),
                    isDense: true,
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  ),
                ),
              ),
              const SizedBox(height: 10),
              Expanded(
                child: () {
                  if (_loading) return const Center(child: CircularProgressIndicator());
                  if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
                  return _Card(
                    child: filtered.isEmpty
                        ? Center(child: Padding(padding: const EdgeInsets.all(20), child: Text(_t("Mijozlar yo'q", "Mijozlar yo'q"))))
                        : ListView.separated(
                            shrinkWrap: true,
                            itemCount: filtered.length,
                            separatorBuilder: (_, __) => const Divider(height: 16),
                            itemBuilder: (_, i) {
                              final c = Map<String, dynamic>.from(filtered[i] as Map);
                              final initial = (('${c['name'] ?? '?'}').trim().isNotEmpty)
                                  ? ('${c['name']}'.trim()[0]).toUpperCase()
                                  : '?';
                              return Row(
                                crossAxisAlignment: CrossAxisAlignment.center,
                                children: [
                                  CircleAvatar(
                                    radius: 24,
                                    backgroundColor: const Color(0xFF7EA8FF),
                                    child: Text(
                                      initial,
                                      style: const TextStyle(
                                        color: Colors.white,
                                        fontWeight: FontWeight.w700,
                                        fontSize: 20,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          '${c['name'] ?? ''}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            fontWeight: FontWeight.w700,
                                            fontSize: 15,
                                          ),
                                        ),
                                        Text(
                                          '🪪 ${c['passport_id'] ?? ''}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            color: Color(0xFF475467),
                                            fontSize: 13,
                                          ),
                                        ),
                                        Text(
                                          '📞 ${c['contact'] ?? ''}',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(
                                            color: Color(0xFF475467),
                                            fontSize: 13,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  const SizedBox(width: 6),
                                  Column(
                                    children: [
                                      OutlinedButton.icon(
                                        onPressed: () => _editCustomer(c),
                                        style: OutlinedButton.styleFrom(
                                          minimumSize: const Size(82, 34),
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                                        ),
                                        icon: const Text('✏️', style: TextStyle(fontSize: 12)),
                                        label: Text(_t('Изм.', 'Tahr.'), style: const TextStyle(fontSize: 12)),
                                      ),
                                      const SizedBox(height: 6),
                                      FilledButton(
                                        style: FilledButton.styleFrom(
                                          backgroundColor: const Color(0xFFE5534B),
                                          minimumSize: const Size(82, 34),
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                                        ),
                                        onPressed: () => _deleteCustomer(c),
                                        child: const Text('🗑', style: TextStyle(fontSize: 14)),
                                      ),
                                    ],
                                  ),
                                ],
                              );
                            },
                          ),
                  );
                }(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RefundsSheet extends StatefulWidget {
  const _RefundsSheet({
    required this.api,
    required this.initialYear,
    required this.initialMonth,
  });

  final _ApiClient api;
  final int initialYear;
  final int initialMonth;

  @override
  State<_RefundsSheet> createState() => _RefundsSheetState();
}

class _RefundsSheetState extends State<_RefundsSheet> {
  late int _year = widget.initialYear;
  late int _month = widget.initialMonth;
  bool _loading = true;
  String? _error;
  List<dynamic> _rows = [];
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  String _apiDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  DateTime _firstDay() => DateTime(_year, _month, 1);
  DateTime _lastDay() => DateTime(_year, _month + 1, 0);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/refunds/list', query: {
        'branch_id': widget.api.branchId.toString(),
        'from_date': _apiDate(_firstDay()),
        'to_date': _apiDate(_lastDay()),
      });
      setState(() => _rows = (data as List).cast<dynamic>());
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 8),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.72,
          child: Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(8, 0, 4, 6),
                child: Row(
                  children: [
                    Text('↩️ ${_t('Возвраты', 'Qaytarishlar')}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    const Spacer(),
                    IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                  ],
                ),
              ),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      value: _month,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                      ),
                      items: List.generate(12, (i) => i + 1)
                          .map((m) => DropdownMenuItem(value: m, child: Text('$m')))
                          .toList(),
                      onChanged: (v) => setState(() => _month = v ?? _month),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      value: _year,
                      decoration: const InputDecoration(
                        border: OutlineInputBorder(),
                        isDense: true,
                        contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
                      ),
                      items: List.generate(11, (i) => DateTime.now().year - 5 + i)
                          .map((y) => DropdownMenuItem(value: y, child: Text('$y')))
                          .toList(),
                      onChanged: (v) => setState(() => _year = v ?? _year),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    onPressed: _load,
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFF3D8BDF), padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12)),
                    child: Text(_t('Поиск', 'Izlash')),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Expanded(
                child: () {
                  if (_loading) return const Center(child: CircularProgressIndicator());
                  if (_error != null) return Center(child: Text(_error!, style: const TextStyle(color: Colors.red)));
                  if (_rows.isEmpty) {
                    return Center(
                      child: Text(
                        trPair(ru: 'За выбранный период возвратов нет', uz: "Tanlangan davrda qaytargan mablag'lar yo'q"),
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 16, color: Color(0xFF64748B)),
                      ),
                    );
                  }
                  return ListView.separated(
                    itemCount: _rows.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final r = Map<String, dynamic>.from(_rows[i] as Map);
                      return _Card(
                        child: Row(
                          children: [
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${r['refund_reason'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16)),
                                  const SizedBox(height: 4),
                                  Text('${r['created_at'] ?? ''}', style: const TextStyle(color: Color(0xFF64748B))),
                                ],
                              ),
                            ),
                            Text('${r['refund_amount'] ?? 0}',
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18, color: Color(0xFFC0392B))),
                          ],
                        ),
                      );
                    },
                  );
                }(),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SettingsPage extends StatefulWidget {
  const _SettingsPage({required this.api});
  final _ApiClient api;

  @override
  State<_SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<_SettingsPage> {
  static const int _rootTelegramId = 1343842535;

  bool _loading = true;
  String? _error;
  bool _isAdmin = false;
  bool _isRootAdmin = false;
  String _language = 'ru';
  bool _myNotify = false;
  bool _userNotify = false;
  bool _prepayEnabled = false;
  String _prepayMode = 'percent';
  final _prepayValueCtrl = TextEditingController(text: '0');
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);
  bool _saving = false;

  final _newUserCtrl = TextEditingController();
  final _newUserTelegramCtrl = TextEditingController();
  final _newUserPasswordCtrl = TextEditingController();
  final _oldPassCtrl = TextEditingController();
  final _newPassCtrl = TextEditingController();
  final _confirmPassCtrl = TextEditingController();
  final _newBranchNameCtrl = TextEditingController();
  final _newBranchAddressCtrl = TextEditingController();
  final _newBranchLatCtrl = TextEditingController();
  final _newBranchLngCtrl = TextEditingController();
  final ImagePicker _imagePicker = ImagePicker();

  List<Map<String, dynamic>> _users = [];
  List<Map<String, dynamic>> _branches = [];
  int? _selectedUserId;
  int? _selectedBranchId;

  bool get _canManage => _isAdmin;

  @override
  void initState() {
    super.initState();
    _loadRole();
  }

  @override
  void dispose() {
    _newUserCtrl.dispose();
    _newUserTelegramCtrl.dispose();
    _newUserPasswordCtrl.dispose();
    _oldPassCtrl.dispose();
    _newPassCtrl.dispose();
    _confirmPassCtrl.dispose();
    _newBranchNameCtrl.dispose();
    _newBranchAddressCtrl.dispose();
    _newBranchLatCtrl.dispose();
    _newBranchLngCtrl.dispose();
    _prepayValueCtrl.dispose();
    super.dispose();
  }

  void _snack(String text, {bool error = false}) {
    showAppAlert(context, text, error: error);
  }

  String _friendlyError(Object e) {
    final raw = '$e';
    final lower = raw.toLowerCase();

    if (lower.contains('socketexception') ||
        lower.contains('failed host lookup') ||
        lower.contains('timeoutexception') ||
        lower.contains('future not completed') ||
        lower.contains('network')) {
      return friendlyErrorText(raw, lang: _language);
    }

    if (lower.contains('username already exists')) {
      return _t('Пользователь с таким именем уже существует', 'Bunday foydalanuvchi nomi allaqachon mavjud');
    }
    if (lower.contains('telegram') && lower.contains('already exists')) {
      return _t('Этот Telegram ID уже используется', 'Bu Telegram ID allaqachon ishlatilgan');
    }
    if (lower.contains('permission') || lower.contains('forbidden') || lower.contains('status 403')) {
      return _t('У вас нет доступа для этого действия', 'Bu amal uchun sizda ruxsat yo‘q');
    }
    if (lower.contains('status 401')) {
      return _t('Сессия истекла. Войдите снова', 'Sessiya tugadi. Qayta kiring');
    }

    final m = RegExp(r'"detail"\s*:\s*"([^"]+)"').firstMatch(raw);
    if (m != null && m.groupCount >= 1) {
      return m.group(1) ?? raw;
    }

    return _t('Произошла ошибка. Попробуйте ещё раз', 'Xatolik yuz berdi. Qayta urinib ko‘ring');
  }

  int? _toInt(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse('${v ?? ''}');
  }

  Future<void> _loadRole() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final me = Map<String, dynamic>.from(await widget.api.getJson('/auth/me') as Map);
      final tg = _toInt(me['telegram_id']) ?? 0;
      final rootById = tg == _rootTelegramId;

      bool rootByEndpoint = false;
      try {
        await widget.api.getJson('/root/system-expiry');
        rootByEndpoint = true;
      } catch (_) {
        rootByEndpoint = false;
      }

      bool myNotify = false;
      String lang = '${me['language'] ?? 'ru'}';
      try {
        final prefs = Map<String, dynamic>.from(await widget.api.getJson('/users/me/preferences') as Map);
        myNotify = prefs['notify_enabled'] == true;
        lang = '${prefs['language'] ?? lang}';
      } catch (_) {}

      List<Map<String, dynamic>> users = [];
      List<Map<String, dynamic>> branches = [];
      if (me['is_admin'] == true) {
        try {
          final u = await widget.api.getJson('/users');
          if (u is List) {
            users = u.whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
          }
        } catch (_) {}
        branches = await _loadAdminBranches();
        await _loadPrepaymentSettings();
      }

      setState(() {
        _isAdmin = me['is_admin'] == true;
        _isRootAdmin = rootById || rootByEndpoint;
        _language = lang;
        _myNotify = myNotify;
        _users = users;
        _branches = branches;
        _selectedUserId = users.isNotEmpty ? _toInt(users.first['id']) : null;
        _selectedBranchId = branches.isNotEmpty ? _toInt(branches.first['id']) : null;
      });
      await _loadSelectedUserNotify();
    } catch (e) {
      setState(() => _error = _friendlyError(e));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<List<Map<String, dynamic>>> _loadAdminBranches() async {
    final out = <Map<String, dynamic>>[];
    final paths = <String>['/branches/admin', '/branches'];
    for (final p in paths) {
      try {
        final b = await widget.api.getJson(p);
        if (b is List) {
          for (final row in b.whereType<Map>()) {
            final m = Map<String, dynamic>.from(row);
            final id = _toInt(m['id'] ?? m['branch_id']);
            if (id == null) continue;
            out.add({
              'id': id,
              'name': '${m['name'] ?? m['branch_name'] ?? id}',
            });
          }
          if (out.isNotEmpty) return out;
        }
      } catch (_) {}
    }
    return out;
  }

  Map<String, String> _collectNameSlug(String nameKey, String slugKey) {
    final map = <String, String>{};
    for (final b in _branches) {
      final name = '${b[nameKey] ?? ''}'.trim();
      final slug = '${b[slugKey] ?? ''}'.trim();
      if (name.isNotEmpty && slug.isNotEmpty) {
        map[name] = slug;
      }
    }
    return map;
  }

  String _slugify(String input) {
    final raw = input.trim().toLowerCase();
    final slug = raw.replaceAll(RegExp(r'[^a-z0-9]+'), '-').replaceAll(RegExp(r'^-+|-+$'), '');
    return slug.isEmpty ? raw : slug;
  }

  Future<void> _openBranchEditor({Map<String, dynamic>? branch}) async {
    final regions = _collectNameSlug('region_name', 'region_slug');
    final cities = _collectNameSlug('city_name', 'city_slug');
    final districts = _collectNameSlug('district_name', 'district_slug');

    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => _BranchEditorSheet(
        api: widget.api,
        imagePicker: _imagePicker,
        initialBranch: branch,
        regionMap: regions,
        cityMap: cities,
        districtMap: districts,
        slugify: _slugify,
      ),
    );
    if (ok == true) {
      await _loadRole();
    }
  }

  Future<void> _loadSelectedUserNotify() async {
    if (!_canManage || _selectedUserId == null) return;
    try {
      final u = Map<String, dynamic>.from(await widget.api.getJson('/users/$_selectedUserId') as Map);
      if (!mounted) return;
      setState(() => _userNotify = u['notify_enabled'] == true);
    } catch (_) {}
  }

  Future<void> _loadPrepaymentSettings() async {
    try {
      final cfg = Map<String, dynamic>.from(await widget.api.getJson('/settings/booking-prepayment') as Map);
      if (!mounted) return;
      setState(() {
        _prepayEnabled = cfg['enabled'] == true;
        _prepayMode = '${cfg['mode'] ?? 'percent'}';
        _prepayValueCtrl.text = '${cfg['value'] ?? 0}';
      });
    } catch (_) {}
  }

  Future<void> _savePrepaymentSettings() async {
    final value = double.tryParse(_prepayValueCtrl.text.trim()) ?? 0;
    setState(() => _saving = true);
    try {
      await widget.api.postJson('/settings/booking-prepayment', {
        'enabled': _prepayEnabled,
        'mode': _prepayMode,
        'value': value,
      });
      _snack(_t('Настройки сохранены', 'Sozlamalar saqlandi'));
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _createUser() async {
    final username = _newUserCtrl.text.trim();
    final password = _newUserPasswordCtrl.text.trim();
    final tg = _newUserTelegramCtrl.text.trim();
    if (username.isEmpty || password.isEmpty || tg.isEmpty) {
      _snack('Fill username, password and telegram ID', error: true);
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.api.postJson('/users', {
        'username': username,
        'password': password,
        'telegram_id': tg,
      });
      _newUserCtrl.clear();
      _newUserTelegramCtrl.clear();
      _newUserPasswordCtrl.clear();
      await _loadRole();
      _snack('User created');
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _deleteUser() async {
    if (_selectedUserId == null) return;
    final ok = await confirmAction(
      context,
      title: 'Удалить пользователя',
      message: 'Вы уверены, что хотите удалить пользователя?',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    );
    if (!ok) return;
    setState(() => _saving = true);
    try {
      await widget.api.deleteJson('/users/$_selectedUserId');
      await _loadRole();
      _snack('User deleted');
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _openAssignBranches() async {
    if (_selectedUserId == null) return;
    if (_branches.isEmpty) {
      final loaded = await _loadAdminBranches();
      if (mounted) setState(() => _branches = loaded);
    }
    final assigned = <int>{};
    try {
      final rows = await widget.api.getJson('/users/$_selectedUserId/branches');
      if (rows is List) {
        for (final r in rows.whereType<Map>()) {
          final id = _toInt(r['id']);
          if (id != null) assigned.add(id);
        }
      }
    } catch (_) {}
    final selected = <int>{...assigned};

    final save = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          title: const Text('Assign branches'),
          content: SizedBox(
            width: 360,
            child: _branches.isEmpty
                ? const Padding(
                    padding: EdgeInsets.symmetric(vertical: 12),
                    child: Text('No branches found'),
                  )
                : ListView(
                    shrinkWrap: true,
                    children: _branches.map((b) {
                      final id = _toInt(b['id']) ?? 0;
                      final name = '${b['name'] ?? b['branch_name'] ?? b['id']}';
                      return CheckboxListTile(
                        value: selected.contains(id),
                        title: Text(name),
                        onChanged: (v) => setD(() {
                          if (v == true) {
                            selected.add(id);
                          } else {
                            selected.remove(id);
                          }
                        }),
                      );
                    }).toList(),
                  ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (save != true) return;

    setState(() => _saving = true);
    try {
      final errors = <String>[];
      for (final id in selected.difference(assigned)) {
        try {
          await _assignUserToBranch(id, _selectedUserId!);
        } catch (e) {
          errors.add('Assign branch $id failed: $e');
        }
      }
      for (final id in assigned.difference(selected)) {
        try {
          await _removeUserFromBranch(id, _selectedUserId!);
        } catch (_) {
          // match web behavior: ignore remove failures
        }
      }
      if (errors.isNotEmpty) {
        _snack(errors.first, error: true);
      } else {
        _snack('Branches updated');
      }
      await _loadRole();
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _assignUserToBranch(int branchId, int userId) async {
    try {
      await widget.api.postJson('/branches/$branchId/assign-user', {'user_id': userId});
      return;
    } catch (_) {}
    await widget.api.postJson('/branches/$branchId/assign-user/', {'user_id': userId});
  }

  Future<void> _removeUserFromBranch(int branchId, int userId) async {
    try {
      await widget.api.deleteJson('/branches/$branchId/users/$userId');
      return;
    } catch (_) {}
    await widget.api.deleteJson('/branches/$branchId/users/$userId/');
  }

  Future<void> _createBranch() async {
    final name = _newBranchNameCtrl.text.trim();
    if (name.isEmpty) {
      _snack('Branch name required', error: true);
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.api.postJson('/branches/branches-admin', {
        'name': name,
        'address': _newBranchAddressCtrl.text.trim().isEmpty ? null : _newBranchAddressCtrl.text.trim(),
        'latitude': double.tryParse(_newBranchLatCtrl.text.trim()),
        'longitude': double.tryParse(_newBranchLngCtrl.text.trim()),
      });
      _newBranchNameCtrl.clear();
      _newBranchAddressCtrl.clear();
      _newBranchLatCtrl.clear();
      _newBranchLngCtrl.clear();
      await _loadRole();
      _snack('Branch created');
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _deleteBranch() async {
    if (_selectedBranchId == null) return;
    final ok = await confirmAction(
      context,
      title: 'Удалить филиал',
      message: 'Вы уверены, что хотите удалить филиал?',
      confirmText: 'Удалить',
      cancelText: 'Отмена',
    );
    if (!ok) return;
    setState(() => _saving = true);
    try {
      await widget.api.deleteJson('/branches/admin/$_selectedBranchId');
      await _loadRole();
      _snack('Branch deleted');
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _toggleUserNotify(bool v) async {
    if (_selectedUserId == null) return;
    setState(() => _userNotify = v);
    try {
      await widget.api.postJson('/users/admin/users/$_selectedUserId/notify', {'enabled': v});
    } catch (e) {
      if (!mounted) return;
      setState(() => _userNotify = !v);
      _snack(_friendlyError(e), error: true);
    }
  }

  Future<void> _toggleMyNotify(bool v) async {
    setState(() => _myNotify = v);
    try {
      await widget.api.postJson('/users/me/notify', {'enabled': v});
    } catch (e) {
      if (!mounted) return;
      setState(() => _myNotify = !v);
      _snack(_friendlyError(e), error: true);
    }
  }

  Future<void> _changePassword() async {
    final current = _oldPassCtrl.text.trim();
    final next = _newPassCtrl.text.trim();
    final confirm = _confirmPassCtrl.text.trim();
    if (current.isEmpty || next.isEmpty || confirm.isEmpty) {
      _snack('Fill all password fields', error: true);
      return;
    }
    if (next != confirm) {
      _snack('Passwords do not match', error: true);
      return;
    }
    setState(() => _saving = true);
    try {
      await widget.api.postJson('/settings/change-password', {
        'current_password': current,
        'new_password': next,
      });
      _oldPassCtrl.clear();
      _newPassCtrl.clear();
      _confirmPassCtrl.clear();
      _snack('Password changed');
    } catch (e) {
      _snack(_friendlyError(e), error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _setLanguage(String lang) async {
    lang = normLang(lang);
    if (_language == lang) return;
    final prev = _language;
    setState(() => _language = lang);
    try {
      await widget.api.postJson('/settings/language', {'language': lang});
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString(kLanguageKey, lang);
      appLang.value = lang;
      _snack('Language saved');
    } catch (e) {
      if (mounted) setState(() => _language = prev);
      _snack(_friendlyError(e), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_error != null) {
      return RefreshIndicator(
        onRefresh: _loadRole,
        child: ListView(
          physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
          children: [
            const SizedBox(height: 140),
            _ErrorText(error: _error!),
            const SizedBox(height: 10),
            Center(
              child: Text(
                _t('Потяните вниз, чтобы обновить', 'Yangilash uchun pastga torting'),
                style: const TextStyle(color: Colors.black54, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadRole,
      child: ListView(
        physics: const BouncingScrollPhysics(parent: AlwaysScrollableScrollPhysics()),
        padding: const EdgeInsets.all(16),
        children: [
          Row(
            children: [
              const _WebIcon('settings', size: 20),
              const SizedBox(width: 8),
              _SectionTitle(_t('Настройки', 'Sozlash')),
            ],
          ),
          const SizedBox(height: 10),
          if (_canManage) ...[
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const _WebIcon('user', size: 20),
                      const SizedBox(width: 8),
                      Text(_t('Пользователи', 'Foydalanuvchilar'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  TextField(controller: _newUserCtrl, decoration: InputDecoration(hintText: _t('Имя пользователя', 'Foydalanuvchi nomi'), border: const OutlineInputBorder())),
                  const SizedBox(height: 8),
                  TextField(controller: _newUserTelegramCtrl, decoration: const InputDecoration(hintText: 'Telegram ID', border: OutlineInputBorder())),
                  const SizedBox(height: 8),
                  TextField(controller: _newUserPasswordCtrl, obscureText: true, decoration: InputDecoration(hintText: _t('Пароль', 'Parol'), border: const OutlineInputBorder())),
                ],
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(width: double.infinity, child: FilledButton(onPressed: _saving ? null : _createUser, child: Text(_t('Добавить', "Qo'shish")))),
            const SizedBox(height: 8),
            DropdownButtonFormField<int>(
              value: _selectedUserId,
              decoration: const InputDecoration(border: OutlineInputBorder()),
              items: _users
                  .map((u) => DropdownMenuItem<int>(
                        value: _toInt(u['id']),
                        child: Text('${u['username'] ?? u['name'] ?? u['id']}'),
                      ))
                  .toList(),
              onChanged: (v) async {
                setState(() => _selectedUserId = v);
                await _loadSelectedUserNotify();
              },
            ),
            const SizedBox(height: 8),
            SizedBox(width: double.infinity, child: FilledButton(onPressed: _saving ? null : _openAssignBranches, child: Text(_t('Назначить филиалы', 'Filiallarni biriktirish')))),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
                onPressed: _saving ? null : _deleteUser,
                child: Text(_t("Удалить", "O'chirish")),
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      const _WebIcon('branch', size: 20),
                      const SizedBox(width: 8),
                      Text(_t('Управление филиалами', 'Filial boshqaruvi'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  DropdownButtonFormField<int>(
                    value: _selectedBranchId,
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                    items: _branches
                        .map((b) => DropdownMenuItem<int>(
                              value: _toInt(b['id']),
                              child: Text('${b['id']} - ${b['name'] ?? b['branch_name'] ?? ''}'),
                            ))
                        .toList(),
                    onChanged: (v) => setState(() => _selectedBranchId = v),
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _selectedBranchId == null
                          ? null
                          : () {
                              final branch = _branches.firstWhere(
                                (b) => _toInt(b['id']) == _selectedBranchId,
                                orElse: () => <String, dynamic>{},
                              );
                              _openBranchEditor(branch: branch);
                            },
                      child: Text(_t('Редактировать выбранный филиал', 'Tanlangan filialni tahrirlash')),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF3B82F6)),
                      onPressed: () => _openBranchEditor(),
                      child: Text(_t('Добавить новый филиал', "Yangi filial qo'shish")),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_t('Предоплата для брони', "Bron uchun oldindan to'lov"), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  Row(
                    children: [
                      Expanded(child: Text(_t('Включить', 'Yoqish'))),
                      Switch(
                        value: _prepayEnabled,
                        onChanged: _saving ? null : (v) => setState(() => _prepayEnabled = v),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  DropdownButtonFormField<String>(
                    value: _prepayMode,
                    decoration: const InputDecoration(border: OutlineInputBorder()),
                    items: [
                      DropdownMenuItem(value: 'percent', child: Text(_t('Процент', 'Foiz'))),
                      DropdownMenuItem(value: 'fixed', child: Text(_t('Фиксированная сумма', "Qat'iy summa"))),
                    ],
                    onChanged: _saving ? null : (v) => setState(() => _prepayMode = v ?? 'percent'),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _prepayValueCtrl,
                    keyboardType: const TextInputType.numberWithOptions(decimal: true),
                    decoration: InputDecoration(
                      hintText: _prepayMode == 'percent' ? _t('Значение в %', 'Qiymat %') : _t('Сумма', 'Summa'),
                      border: const OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 8),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: _saving ? null : _savePrepaymentSettings,
                      child: Text(_t('Сохранить', 'Saqlash')),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_t('Отчеты по филиалам', 'Filial hisobotlari'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF4F46E5)),
                      onPressed: () async {
                        await showModalBottomSheet(
                          context: context,
                          isScrollControlled: true,
                          backgroundColor: Colors.white,
                          shape: const RoundedRectangleBorder(
                            borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                          ),
                          builder: (_) => _AdminReportsSheet(api: widget.api),
                        );
                      },
                      child: Text(_t('Открыть отчеты', 'Hisobotlarni ochish')),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (_isRootAdmin) ...[
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Root Admin', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF4F46E5)),
                      onPressed: () async {
                        await showModalBottomSheet(
                          context: context,
                          isScrollControlled: true,
                          backgroundColor: Colors.white,
                          shape: const RoundedRectangleBorder(
                            borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                          ),
                          builder: (_) => _RootAdminSheet(api: widget.api),
                        );
                      },
                      child: const Text('Open Root Management'),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
          ],
          if (_canManage)
            Row(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      const _WebIcon('bell', size: 18),
                      const SizedBox(width: 8),
                      Text(_t('Уведомления пользователя', 'Foydalanuvchi bildirishnomalari'), style: const TextStyle(fontSize: 16)),
                    ],
                  ),
                ),
                Checkbox(value: _userNotify, onChanged: (v) => _toggleUserNotify(v ?? false)),
              ],
            ),
          const SizedBox(height: 8),
          _Card(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const _WebIcon('locked', size: 20),
                    const SizedBox(width: 8),
                    Text(_t('Изменить пароль', "Parolni o'zgartirish"), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 10),
                TextField(controller: _oldPassCtrl, obscureText: true, decoration: InputDecoration(hintText: _t('Текущий пароль', 'Joriy parol'), border: const OutlineInputBorder())),
                const SizedBox(height: 8),
                TextField(controller: _newPassCtrl, obscureText: true, decoration: InputDecoration(hintText: _t('Новый пароль', 'Yangi parol'), border: const OutlineInputBorder())),
                const SizedBox(height: 8),
                TextField(controller: _confirmPassCtrl, obscureText: true, decoration: InputDecoration(hintText: _t('Подтвердите пароль', 'Parolni tasdiqlang'), border: const OutlineInputBorder())),
              ],
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
              onPressed: _saving ? null : _changePassword,
              child: Text(_t('Сохранить', 'Saqlash')),
            ),
          ),
          const SizedBox(height: 12),
          _Card(
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          const _WebIcon('bell', size: 20),
                          const SizedBox(width: 8),
                          Text(_t('Уведомления', 'Bildirishnomalar'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Text(_t('Уведомления о задолженности', "Qarzdorlik bo'yicha bildirishnomalar")),
                    ],
                  ),
                ),
                Checkbox(value: _myNotify, onChanged: (v) => _toggleMyNotify(v ?? false)),
              ],
            ),
            ),
            const SizedBox(height: 12),
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(_t('Отзывы клиентов', 'Mijoz fikrlari'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF059669)),
                      onPressed: () async {
                        await showModalBottomSheet(
                          context: context,
                          isScrollControlled: true,
                          backgroundColor: Colors.white,
                          shape: const RoundedRectangleBorder(
                            borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
                          ),
                          builder: (_) => _AdminFeedbackSheet(api: widget.api),
                        );
                      },
                      child: Text(_t('Открыть отзывы', 'Fikrlarni ochish')),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                Row(
                  children: [
                    const _WebIcon('language', size: 20),
                    const SizedBox(width: 8),
                    Text(_t('Язык', 'Til'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  ],
                ),
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: _language == 'ru' ? const Color(0xFF2563EB) : Colors.white,
                          foregroundColor: _language == 'ru' ? Colors.white : Colors.black87,
                          side: BorderSide(color: _language == 'ru' ? const Color(0xFF2563EB) : const Color(0xFFD1D5DB)),
                        ),
                        onPressed: _saving ? null : () => _setLanguage('ru'),
                        child: const Text('ru Русский'),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: _language == 'uz' ? const Color(0xFF2563EB) : Colors.white,
                          foregroundColor: _language == 'uz' ? Colors.white : Colors.black87,
                          side: BorderSide(color: _language == 'uz' ? const Color(0xFF2563EB) : const Color(0xFFD1D5DB)),
                        ),
                        onPressed: _saving ? null : () => _setLanguage('uz'),
                        child: const Text("uz O'zbekcha"),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _BranchEditorSheet extends StatefulWidget {
  const _BranchEditorSheet({
    required this.api,
    required this.imagePicker,
    required this.regionMap,
    required this.cityMap,
    required this.districtMap,
    required this.slugify,
    this.initialBranch,
  });

  final _ApiClient api;
  final ImagePicker imagePicker;
  final Map<String, String> regionMap;
  final Map<String, String> cityMap;
  final Map<String, String> districtMap;
  final String Function(String) slugify;
  final Map<String, dynamic>? initialBranch;

  @override
  State<_BranchEditorSheet> createState() => _BranchEditorSheetState();
}

class _BranchEditorSheetState extends State<_BranchEditorSheet> {
  final _nameCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _regionCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _districtCtrl = TextEditingController();
  final _latCtrl = TextEditingController();
  final _lngCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _telegramCtrl = TextEditingController();

  String? _regionSlug;
  String? _citySlug;
  String? _districtSlug;
  int? _branchId;
  bool _saving = false;
  bool _loadingImages = false;
  bool _uploadingImage = false;
  List<Map<String, dynamic>> _images = [];

  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    final b = widget.initialBranch;
    if (b != null && b.isNotEmpty) {
      _branchId = b['id'] is int ? b['id'] as int : int.tryParse('${b['id']}');
      _nameCtrl.text = '${b['name'] ?? b['branch_name'] ?? ''}';
      _addressCtrl.text = '${b['address'] ?? ''}';
      _regionCtrl.text = '${b['region_name'] ?? ''}';
      _cityCtrl.text = '${b['city_name'] ?? ''}';
      _districtCtrl.text = '${b['district_name'] ?? ''}';
      _latCtrl.text = '${b['latitude'] ?? ''}';
      _lngCtrl.text = '${b['longitude'] ?? ''}';
      _phoneCtrl.text = '${b['contact_phone'] ?? ''}';
      _telegramCtrl.text = '${b['contact_telegram'] ?? ''}';
      _regionSlug = '${b['region_slug'] ?? ''}';
      _citySlug = '${b['city_slug'] ?? ''}';
      _districtSlug = '${b['district_slug'] ?? ''}';
      _loadImages();
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _addressCtrl.dispose();
    _regionCtrl.dispose();
    _cityCtrl.dispose();
    _districtCtrl.dispose();
    _latCtrl.dispose();
    _lngCtrl.dispose();
    _phoneCtrl.dispose();
    _telegramCtrl.dispose();
    super.dispose();
  }

  String _imgUrl(dynamic imagePath) {
    final raw = '${imagePath ?? ''}'.trim();
    if (raw.isEmpty) return '';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    if (raw.startsWith('/')) return 'https://hmsuz.com$raw';
    return 'https://hmsuz.com/$raw';
  }

  Future<void> _loadImages() async {
    final id = _branchId;
    if (id == null) return;
    setState(() => _loadingImages = true);
    try {
      final rows = await widget.api.listBranchImages(id);
      if (!mounted) return;
      setState(() => _images = rows);
    } catch (_) {
      if (!mounted) return;
      setState(() => _images = []);
    } finally {
      if (mounted) setState(() => _loadingImages = false);
    }
  }

  String? _slugFor(String name, Map<String, String> map) {
    final trimmed = name.trim();
    if (trimmed.isEmpty) return null;
    return map[trimmed] ?? widget.slugify(trimmed);
  }

  Future<void> _pickLocation() async {
    final lat = double.tryParse(_latCtrl.text.trim());
    final lng = double.tryParse(_lngCtrl.text.trim());
    final picked = await showModalBottomSheet<LatLng>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(18)),
      ),
      builder: (_) => _BranchMapPickerSheet(
        initial: (lat != null && lng != null) ? LatLng(lat, lng) : null,
      ),
    );
    if (picked != null) {
      setState(() {
        _latCtrl.text = picked.latitude.toStringAsFixed(6);
        _lngCtrl.text = picked.longitude.toStringAsFixed(6);
      });
    }
  }

  Future<void> _save() async {
    final name = _nameCtrl.text.trim();
    final region = _regionCtrl.text.trim();
    final city = _cityCtrl.text.trim();
    final lat = double.tryParse(_latCtrl.text.trim());
    final lng = double.tryParse(_lngCtrl.text.trim());
    if (name.isEmpty) {
      showAppAlert(context, _t('Введите название филиала', 'Filial nomini kiriting'), error: true);
      return;
    }
    if (region.isEmpty || city.isEmpty) {
      showAppAlert(context, _t('Выберите область и город', 'Viloyat va shaharni tanlang'), error: true);
      return;
    }
    if (lat == null || lng == null) {
      showAppAlert(context, _t('Укажите координаты', 'Koordinatalarni kiriting'), error: true);
      return;
    }
    setState(() => _saving = true);
    try {
      _regionSlug = _slugFor(region, widget.regionMap) ?? region;
      _citySlug = _slugFor(city, widget.cityMap) ?? city;
      _districtSlug = _districtCtrl.text.trim().isEmpty
          ? null
          : (_slugFor(_districtCtrl.text.trim(), widget.districtMap) ?? _districtCtrl.text.trim());

      final payload = {
        'name': name,
        'address': _addressCtrl.text.trim().isEmpty ? null : _addressCtrl.text.trim(),
        'latitude': lat,
        'longitude': lng,
        'region_name': region,
        'region_slug': _regionSlug,
        'city_name': city,
        'city_slug': _citySlug,
        'district_name': _districtCtrl.text.trim().isEmpty ? null : _districtCtrl.text.trim(),
        'district_slug': _districtSlug,
        'contact_phone': _phoneCtrl.text.trim().isEmpty ? null : _phoneCtrl.text.trim(),
        'contact_telegram': _telegramCtrl.text.trim().isEmpty ? null : _telegramCtrl.text.trim(),
      };

      if (_branchId == null) {
        final res = await widget.api.postJson('/branches/branches-admin', payload);
        final newId = res is Map ? int.tryParse('${res['branch_id']}') : null;
        if (newId != null) {
          setState(() => _branchId = newId);
          await _loadImages();
        }
      } else {
        await widget.api.putJson('/branches/admin/$_branchId', payload);
      }

      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (e) {
      showAppAlert(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _pickAndUploadImage() async {
    final id = _branchId;
    if (id == null) {
      showAppAlert(context, _t('Сначала сохраните филиал', 'Avval filialni saqlang'), error: true);
      return;
    }
    final picked = await widget.imagePicker.pickImage(
      source: ImageSource.gallery,
      imageQuality: 88,
      maxWidth: 1800,
    );
    if (picked == null) return;
    setState(() => _uploadingImage = true);
    try {
      await widget.api.uploadBranchImage(id, filePath: picked.path, isCover: _images.isEmpty);
      await _loadImages();
      showAppAlert(context, _t('Фото загружено', 'Rasm yuklandi'));
    } catch (e) {
      showAppAlert(context, '$e', error: true);
    } finally {
      if (mounted) setState(() => _uploadingImage = false);
    }
  }

  Future<void> _setCover(Map<String, dynamic> img) async {
    final id = _branchId;
    final imgId = img['id'] is int ? img['id'] as int : int.tryParse('${img['id']}');
    if (id == null || imgId == null) return;
    await widget.api.setBranchImageCover(id, imgId);
    await _loadImages();
  }

  Future<void> _deleteImage(Map<String, dynamic> img) async {
    final id = _branchId;
    final imgId = img['id'] is int ? img['id'] as int : int.tryParse('${img['id']}');
    if (id == null || imgId == null) return;
    await widget.api.deleteBranchImage(id, imgId);
    await _loadImages();
  }

  Future<void> _deleteBranch() async {
    final id = _branchId;
    if (id == null) return;
    final ok = await confirmAction(
      context,
      title: _t('Удалить филиал', 'Filialni o‘chirish'),
      message: _t('Вы уверены, что хотите удалить филиал?', 'Filialni o‘chirmoqchimisiz?'),
      confirmText: _t('Удалить', "O'chirish"),
      cancelText: _t('Отмена', 'Bekor'),
    );
    if (!ok) return;
    try {
      await widget.api.deleteJson('/branches/admin/$id');
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      showAppAlert(context, '$e', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    final isEdit = _branchId != null;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          left: 16,
          right: 16,
          top: 12,
          bottom: MediaQuery.of(context).viewInsets.bottom + 16,
        ),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    isEdit ? _t('Редактирование филиала', 'Filial tahrirlash') : _t('Новый филиал', 'Yangi filial'),
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
                  ),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close)),
                ],
              ),
              const SizedBox(height: 8),
              TextField(controller: _nameCtrl, decoration: InputDecoration(hintText: _t('Название', 'Nomi'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _addressCtrl, decoration: InputDecoration(hintText: _t('Адрес (необязательно)', 'Manzil (ixtiyoriy)'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _regionCtrl, decoration: InputDecoration(hintText: _t('Область', 'Viloyat'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _cityCtrl, decoration: InputDecoration(hintText: _t('Город', 'Shahar'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _districtCtrl, decoration: InputDecoration(hintText: _t('Район', 'Tuman'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _latCtrl, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: InputDecoration(hintText: _t('Широта', 'Kenglik'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _lngCtrl, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: InputDecoration(hintText: _t('Долгота', 'Uzunlik'), border: const OutlineInputBorder())),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton(
                  onPressed: _pickLocation,
                  child: Text(_t('Выбрать точку на карте', 'Xaritadan tanlash')),
                ),
              ),
              const SizedBox(height: 8),
              TextField(controller: _phoneCtrl, decoration: const InputDecoration(hintText: '+998...', border: OutlineInputBorder())),
              const SizedBox(height: 8),
              TextField(controller: _telegramCtrl, decoration: InputDecoration(hintText: _t('Telegram филиала (необязательно)', 'Filial Telegram (ixtiyoriy)'), border: const OutlineInputBorder())),
              const SizedBox(height: 12),
              Text(_t('Основные фото филиала', 'Filial fotosi'), style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Row(
                children: [
                  FilledButton(
                    onPressed: _uploadingImage ? null : _pickAndUploadImage,
                    child: _uploadingImage
                        ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                        : Text(_t('Загрузить', 'Yuklash')),
                  ),
                  const SizedBox(width: 12),
                  Text(_t('Максимум 3 фото', 'Maksimum 3 foto'), style: const TextStyle(color: Color(0xFF64748B))),
                ],
              ),
              const SizedBox(height: 8),
              if (_loadingImages)
                const Center(child: CircularProgressIndicator())
              else if (_images.isEmpty)
                Text(_t('Фото пока нет', 'Hali rasm yo‘q'), style: const TextStyle(color: Color(0xFF64748B)))
              else
                Column(
                  children: _images.map((img) {
                    final isCover = img['is_cover'] == true;
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Container(
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Column(
                          children: [
                            ClipRRect(
                              borderRadius: const BorderRadius.vertical(top: Radius.circular(12)),
                              child: Image.network(
                                _imgUrl(img['image_path']),
                                height: 160,
                                width: double.infinity,
                                fit: BoxFit.cover,
                              ),
                            ),
                            Padding(
                              padding: const EdgeInsets.all(8),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: FilledButton(
                                      onPressed: isCover ? null : () => _setCover(img),
                                      child: Text(isCover ? _t('Основное', 'Asosiy') : _t('Сделать основным', 'Asosiy qilish')),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  Expanded(
                                    child: OutlinedButton(
                                      onPressed: () => _deleteImage(img),
                                      child: Text(_t('Удалить', "O'chirish")),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }).toList(),
                ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => Navigator.of(context).pop(),
                      child: Text(_t('Отмена', 'Bekor')),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: FilledButton(
                      onPressed: _saving ? null : _save,
                      child: _saving
                          ? const SizedBox(height: 16, width: 16, child: CircularProgressIndicator(strokeWidth: 2))
                          : Text(_t('Сохранить', 'Saqlash')),
                    ),
                  ),
                ],
              ),
              if (isEdit) ...[
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
                    onPressed: _deleteBranch,
                    child: Text(_t('Удалить', "O'chirish")),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _BranchMapPickerSheet extends StatefulWidget {
  const _BranchMapPickerSheet({this.initial});
  final LatLng? initial;

  @override
  State<_BranchMapPickerSheet> createState() => _BranchMapPickerSheetState();
}

class _BranchMapPickerSheetState extends State<_BranchMapPickerSheet> {
  mb.MapboxMap? _map;
  LatLng? _selected;

  @override
  void initState() {
    super.initState();
    _selected = widget.initial;
  }

  void _onTap(mb.MapContentGestureContext ctx) async {
    final coords = ctx.point.coordinates;
    setState(() => _selected = LatLng(coords.lat.toDouble(), coords.lng.toDouble()));
    if (_map != null) {
      await _map!.setCamera(
        mb.CameraOptions(center: mb.Point(coordinates: mb.Position(coords.lng, coords.lat)), zoom: 13),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final token = dotenv.get('MAPBOX_TOKEN', fallback: '');
    return SafeArea(
      child: Column(
        children: [
          const SizedBox(height: 8),
          Text(trPair(ru: 'Выбор точки', uz: 'Nuqtani tanlash', lang: appLang.value),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          Expanded(
            child: token.isEmpty
                ? Center(child: Text(trPair(ru: 'MAPBOX_TOKEN не задан.', uz: 'MAPBOX_TOKEN yo‘q.', lang: appLang.value)))
                : Stack(
                    children: [
                      Builder(
                        builder: (_) {
                          mb.MapboxOptions.setAccessToken(token);
                          return const SizedBox.shrink();
                        },
                      ),
                      mb.MapWidget(
                        key: const ValueKey('branch_map_picker'),
                        styleUri: mb.MapboxStyles.STANDARD,
                        cameraOptions: _selected == null
                            ? mb.CameraOptions(center: mb.Point(coordinates: mb.Position(69.2797, 41.3111)), zoom: 11)
                            : mb.CameraOptions(
                                center: mb.Point(coordinates: mb.Position(_selected!.longitude, _selected!.latitude)),
                                zoom: 13,
                              ),
                        onMapCreated: (map) {
                          _map = map;
                        },
                        onTapListener: _onTap,
                      ),
                      const Center(
                        child: Icon(Icons.place, size: 32, color: Color(0xFFEF4444)),
                      ),
                    ],
                  ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(context).pop(),
                    child: Text(trPair(ru: 'Отмена', uz: 'Bekor', lang: appLang.value)),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: FilledButton(
                    onPressed: _selected == null ? null : () => Navigator.of(context).pop(_selected),
                    child: Text(trPair(ru: 'Выбрать', uz: 'Tanlash', lang: appLang.value)),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _AdminReportsSheet extends StatefulWidget {
  const _AdminReportsSheet({required this.api});
  final _ApiClient api;

  @override
  State<_AdminReportsSheet> createState() => _AdminReportsSheetState();
}

class _AdminReportsSheetState extends State<_AdminReportsSheet> {
  bool _loading = true;
  String? _error;
  String _scope = 'month';
  int _year = DateTime.now().year;
  int _month = DateTime.now().month;
  Map<String, dynamic> _totals = {};
  List<Map<String, dynamic>> _rows = [];

  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);
  String _fmt(dynamic x) {
    final n = (x as num?)?.toDouble() ?? double.tryParse('$x') ?? 0;
    return n.toStringAsFixed(0);
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final q = <String, String>{'scope': _scope};
      if (_scope != 'total') q['year'] = _year.toString();
      if (_scope == 'month') q['month'] = _month.toString();
      final data = await widget.api.getJson('/admin-reports/finance', query: q) as Map;
      setState(() {
        _totals = Map<String, dynamic>.from((data['totals'] as Map?) ?? {});
        _rows = ((data['branches'] as List?) ?? []).cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      });
    } catch (e) {
      setState(() => _error = friendlyErrorText('$e', lang: appLang.value));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Widget _metric(String label, dynamic value) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
          const SizedBox(height: 4),
          Text(_fmt(value), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(12, 12, 12, MediaQuery.of(context).viewInsets.bottom + 12),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.88,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(_t('Отчеты по филиалам', 'Filial hisobotlari'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<String>(
                      value: _scope,
                      decoration: const InputDecoration(border: OutlineInputBorder()),
                      items: [
                        DropdownMenuItem(value: 'month', child: Text(_t('Месяц', 'Oy'))),
                        DropdownMenuItem(value: 'year', child: Text(_t('Год', 'Yil'))),
                        DropdownMenuItem(value: 'total', child: Text(_t('Общий', 'Umumiy'))),
                      ],
                      onChanged: (v) => setState(() => _scope = v ?? 'month'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  if (_scope != 'total')
                    SizedBox(
                      width: 92,
                      child: TextFormField(
                        initialValue: '$_year',
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(border: OutlineInputBorder()),
                        onChanged: (v) => _year = int.tryParse(v) ?? DateTime.now().year,
                      ),
                    ),
                  if (_scope == 'month') ...[
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 76,
                      child: TextFormField(
                        initialValue: '$_month',
                        keyboardType: TextInputType.number,
                        decoration: const InputDecoration(border: OutlineInputBorder()),
                        onChanged: (v) => _month = int.tryParse(v) ?? DateTime.now().month,
                      ),
                    ),
                  ]
                ],
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: FilledButton(onPressed: _load, child: Text(_t('Загрузить', 'Yuklash'))),
              ),
              const SizedBox(height: 10),
              if (_loading) const Expanded(child: Center(child: CircularProgressIndicator())),
              if (!_loading && _error != null) Expanded(child: Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))),
              if (!_loading && _error == null)
                Expanded(
                  child: ListView(
                    children: [
                      GridView.count(
                        crossAxisCount: 2,
                        childAspectRatio: 1.8,
                        mainAxisSpacing: 8,
                        crossAxisSpacing: 8,
                        shrinkWrap: true,
                        physics: const NeverScrollableScrollPhysics(),
                        children: [
                          _metric(_t('Доход', 'Daromad'), _totals['income']),
                          _metric(_t('Расходы', 'Xarajatlar'), _totals['expenses']),
                          _metric(_t('Возвраты', 'Qaytarishlar'), _totals['refunds']),
                          _metric(_t('Долг', 'Qarz'), _totals['debt']),
                          _metric(_t('Прибыль', 'Foyda'), _totals['profit']),
                        ],
                      ),
                      const SizedBox(height: 12),
                      Text(_t('Филиалы', 'Filiallar'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                      const SizedBox(height: 8),
                      if (_rows.isEmpty)
                        Text(_t('Нет данных', "Ma'lumot yo'q"), style: const TextStyle(color: Color(0xFF64748B))),
                      ..._rows.map((r) => _Card(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('${r['branch_id']} - ${r['branch_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                                const SizedBox(height: 6),
                                Text('${_t('Доход', 'Daromad')}: ${_fmt(r['income'])}'),
                                Text('${_t('Расходы', 'Xarajatlar')}: ${_fmt(r['expenses'])}'),
                                Text('${_t('Возвраты', 'Qaytarishlar')}: ${_fmt(r['refunds'])}'),
                                Text('${_t('Долг', 'Qarz')}: ${_fmt(r['debt'])}'),
                                Text('${_t('Прибыль', 'Foyda')}: ${_fmt(r['profit'])}', style: const TextStyle(fontWeight: FontWeight.w700)),
                              ],
                            ),
                          )),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AdminFeedbackSheet extends StatefulWidget {
  const _AdminFeedbackSheet({required this.api});
  final _ApiClient api;

  @override
  State<_AdminFeedbackSheet> createState() => _AdminFeedbackSheetState();
}

class _AdminFeedbackSheetState extends State<_AdminFeedbackSheet> {
  bool _loading = true;
  String? _error;
  List<Map<String, dynamic>> _rows = [];

  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/feedback/admin', query: {'limit': '300'});
      final list = (data as List).cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      setState(() => _rows = list);
    } catch (e) {
      setState(() => _error = friendlyErrorText('$e', lang: appLang.value));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _mark(int id, String status) async {
    try {
      await widget.api.putQuery('/feedback/admin/$id', {
        'status': status,
        'is_read': 'true',
      });
      await _load();
    } catch (e) {
      showAppAlert(context, friendlyErrorText('$e', lang: appLang.value), error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(12, 12, 12, MediaQuery.of(context).viewInsets.bottom + 12),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.85,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(_t('Отзывы клиентов', 'Mijoz fikrlari'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
              const SizedBox(height: 6),
              if (_loading) const Expanded(child: Center(child: CircularProgressIndicator())),
              if (!_loading && _error != null) Expanded(child: Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))),
              if (!_loading && _error == null)
                Expanded(
                  child: _rows.isEmpty
                      ? Center(child: Text(_t('Нет отзывов', "Fikrlar yo'q")))
                      : ListView.separated(
                          itemCount: _rows.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 8),
                          itemBuilder: (_, i) {
                            final r = _rows[i];
                            final id = (r['id'] as num?)?.toInt() ?? 0;
                            return _Card(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('${r['branch_id']} - ${r['branch_name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
                                  const SizedBox(height: 4),
                                  Text('${_t('Клиент', 'Mijoz')}: ${r['user_name'] ?? r['contact'] ?? r['telegram_id'] ?? '—'}'),
                                  Text('${_t('Статус', 'Holat')}: ${r['status'] ?? 'new'}'),
                                  if (r['sentiment'] != null) Text('Sentiment: ${r['sentiment']}'),
                                  const SizedBox(height: 4),
                                  Text('${r['message'] ?? ''}'),
                                  const SizedBox(height: 8),
                                  Row(
                                    children: [
                                      Expanded(
                                        child: OutlinedButton(
                                          onPressed: id > 0 ? () => _mark(id, 'read') : null,
                                          child: Text(_t('Прочитано', "O'qildi")),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: FilledButton(
                                          onPressed: id > 0 ? () => _mark(id, 'resolved') : null,
                                          child: Text(_t('Решено', 'Hal qilindi')),
                                        ),
                                      ),
                                    ],
                                  ),
                                ],
                              ),
                            );
                          },
                        ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RootAdminSheet extends StatefulWidget {
  const _RootAdminSheet({required this.api});
  final _ApiClient api;

  @override
  State<_RootAdminSheet> createState() => _RootAdminSheetState();
}

class _RootAdminSheetState extends State<_RootAdminSheet> {
  bool _loading = true;
  bool _cronBusy = false;
  bool _cronEnabled = true;
  bool _cronForceNext = false;
  String? _error;
  List<Map<String, dynamic>> _admins = [];
  List<Map<String, dynamic>> _branches = [];
  final _search = TextEditingController();
  final _newTg = TextEditingController();
  final _newName = TextEditingController();
  final _newPass = TextEditingController();
  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: appLang.value);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _search.dispose();
    _newTg.dispose();
    _newName.dispose();
    _newPass.dispose();
    super.dispose();
  }

  void _snack(String text, {bool error = false}) {
    final msg = error ? friendlyErrorText(text) : text;
    showAppAlert(context, msg, error: error);
  }

  int? _toInt(dynamic v) {
    if (v is int) return v;
    if (v is num) return v.toInt();
    return int.tryParse('${v ?? ''}');
  }

  String _branchNames(dynamic ids) {
    final list = (ids as List?) ?? const [];
    final idList = list.map((e) => _toInt(e)).whereType<int>().toList();
    if (idList.isEmpty) return '-';
    final names = idList.map((id) {
      final b = _branches.where((e) => _toInt(e['id']) == id).toList();
      if (b.isNotEmpty) return '${b.first['name'] ?? id}';
      return '$id';
    }).toList();
    return names.join(', ');
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final a = await widget.api.getJson('/root/admins');
      final b = await widget.api.getJson('/root/branches');
      bool cronEnabled = _cronEnabled;
      bool cronForceNext = _cronForceNext;
      try {
        final c = Map<String, dynamic>.from(await widget.api.getJson('/root/cron/debt-notify') as Map);
        cronEnabled = c['enabled'] == true;
        cronForceNext = c['force_next_run'] == true;
      } catch (_) {}
      setState(() {
        _admins = (a as List).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
        _branches = (b as List).whereType<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
        _cronEnabled = cronEnabled;
        _cronForceNext = cronForceNext;
      });
    } catch (e) {
      setState(() => _error = friendlyErrorText('$e'));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _createAdmin() async {
    final tg = _newTg.text.trim();
    final pass = _newPass.text.trim();
    final name = _newName.text.trim();
    if (tg.isEmpty || pass.isEmpty) {
      _snack('telegram_id and password required', error: true);
      return;
    }
    try {
      await widget.api.postJson('/root/admins', {
        'telegram_id': int.tryParse(tg) ?? tg,
        'username': name.isEmpty ? null : name,
        'password': pass,
      });
      _newTg.clear();
      _newName.clear();
      _newPass.clear();
      await _load();
      _snack('Admin created');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _setBranches(Map<String, dynamic> admin) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    final selected = <int>{
      ...((admin['branches'] as List?) ?? const []).map((e) => _toInt(e)).whereType<int>(),
    };
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          title: const Text('Filiallar'),
          content: SizedBox(
            width: 360,
            child: ListView(
              shrinkWrap: true,
              children: _branches.map((b) {
                final id = _toInt(b['id']) ?? 0;
                return CheckboxListTile(
                  value: selected.contains(id),
                  title: Text('${b['name'] ?? b['id']}'),
                  onChanged: (v) => setD(() {
                    if (v == true) {
                      selected.add(id);
                    } else {
                      selected.remove(id);
                    }
                  }),
                );
              }).toList(),
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
          ],
        ),
      ),
    );
    if (ok != true) return;
    try {
      await widget.api.postJson('/root/admins/$userId/branches', {'branch_ids': selected.toList()});
      await _load();
      _snack('Branches saved');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _setActive(Map<String, dynamic> admin, bool value) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    try {
      await widget.api.postJson('/root/admins/$userId/set-active', {'is_active': value});
      await _load();
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _setExpiry(Map<String, dynamic> admin) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    final p = await showDatePicker(
      context: context,
      initialDate: DateTime.now().add(const Duration(days: 365)),
      firstDate: DateTime(2020, 1, 1),
      lastDate: DateTime(2100, 12, 31),
    );
    if (p == null) return;
    final iso = '${p.year}-${p.month.toString().padLeft(2, '0')}-${p.day.toString().padLeft(2, '0')}T23:59:59';
    try {
      await widget.api.postJson('/root/admins/$userId/expiry', {'expires_at': iso});
      await _load();
      _snack('Expiry saved');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _clearExpiry(Map<String, dynamic> admin) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    try {
      await widget.api.postJson('/root/admins/$userId/expiry', {'expires_at': null});
      await _load();
      _snack('Expiry cleared');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _resetPassword(Map<String, dynamic> admin) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    final c = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Reset password'),
        content: TextField(controller: c, decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'New password')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Save')),
        ],
      ),
    );
    if (ok != true || c.text.trim().isEmpty) return;
    try {
      await widget.api.postJson('/root/admins/$userId/password', {'password': c.text.trim()});
      _snack('Password reset');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _deleteAdmin(Map<String, dynamic> admin) async {
    final userId = _toInt(admin['id']);
    if (userId == null) return;
    final ok = await confirmAction(
      context,
      title: "Adminni o'chirish",
      message: "Haqiqatan ham adminni o'chirasizmi?",
      confirmText: "O'chirish",
      cancelText: 'Bekor',
    );
    if (!ok) return;
    try {
      await widget.api.deleteJson('/root/admins/$userId');
      await _load();
      _snack('Deleted');
    } catch (e) {
      _snack('$e', error: true);
    }
  }

  Future<void> _saveCronConfig({
    bool? enabled,
    bool? forceNextRun,
  }) async {
    setState(() => _cronBusy = true);
    try {
      final body = <String, dynamic>{};
      if (enabled != null) body['enabled'] = enabled;
      if (forceNextRun != null) body['force_next_run'] = forceNextRun;
      await widget.api.postJson('/root/cron/debt-notify', body);
      final cfg = Map<String, dynamic>.from(await widget.api.getJson('/root/cron/debt-notify') as Map);
      if (!mounted) return;
      setState(() {
        _cronEnabled = cfg['enabled'] == true;
        _cronForceNext = cfg['force_next_run'] == true;
      });
      _snack(_t('Настройки cron сохранены', 'Cron sozlamalari saqlandi'));
    } catch (e) {
      _snack('$e', error: true);
    } finally {
      if (mounted) setState(() => _cronBusy = false);
    }
  }

  Future<void> _runCronTestNow() async {
    setState(() => _cronBusy = true);
    try {
      final res = Map<String, dynamic>.from(
        await widget.api.postJson('/root/cron/debt-notify/test', {'force': true}) as Map,
      );
      final result = Map<String, dynamic>.from((res['result'] as Map?) ?? const {});
      final rows = (result['rows'] as num?)?.toInt() ?? 0;
      final users = (result['processed_users'] as num?)?.toInt() ?? 0;
      _snack('${_t('Тест cron выполнен', 'Cron test ishga tushdi')}: $rows / $users');
      final cfg = Map<String, dynamic>.from(await widget.api.getJson('/root/cron/debt-notify') as Map);
      if (!mounted) return;
      setState(() {
        _cronEnabled = cfg['enabled'] == true;
        _cronForceNext = cfg['force_next_run'] == true;
      });
    } catch (e) {
      _snack('$e', error: true);
    } finally {
      if (mounted) setState(() => _cronBusy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final q = _search.text.trim().toLowerCase();
    final rows = _admins.where((a) {
      if (q.isEmpty) return true;
      final id = '${a['id'] ?? ''}'.toLowerCase();
      final u = '${a['username'] ?? ''}'.toLowerCase();
      final t = '${a['telegram_id'] ?? ''}'.toLowerCase();
      return id.contains(q) || u.contains(q) || t.contains(q);
    }).toList();

    return SafeArea(
      child: Padding(
        padding: EdgeInsets.fromLTRB(10, 10, 10, MediaQuery.of(context).viewInsets.bottom + 8),
        child: SizedBox(
          height: MediaQuery.of(context).size.height * 0.86,
          child: Column(
            children: [
              Row(
                children: [
                  const _WebIcon('root', size: 22),
                  const SizedBox(width: 8),
                  const Text('Root Admin boshqaruvi', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close)),
                ],
              ),
              _Card(
                child: Column(
                  children: [
                    TextField(controller: _search, onChanged: (_) => setState(() {}), decoration: const InputDecoration(hintText: 'ID, username, telegram...', border: OutlineInputBorder())),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(child: TextField(controller: _newTg, decoration: const InputDecoration(hintText: 'Telegram ID', border: OutlineInputBorder()))),
                        const SizedBox(width: 8),
                        Expanded(child: TextField(controller: _newName, decoration: const InputDecoration(hintText: 'Username', border: OutlineInputBorder()))),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(child: TextField(controller: _newPass, obscureText: true, decoration: const InputDecoration(hintText: 'Password', border: OutlineInputBorder()))),
                        const SizedBox(width: 8),
                        FilledButton(onPressed: _createAdmin, child: const Text('+ Admin')),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              _Card(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(_t('Управление debt cron', 'Debt cron boshqaruvi'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(child: Text(_t('Включен', 'Yoqilgan'))),
                        Switch(
                          value: _cronEnabled,
                          onChanged: _cronBusy ? null : (v) => _saveCronConfig(enabled: v),
                        ),
                      ],
                    ),
                    Row(
                      children: [
                        Expanded(child: Text(_t('Принудительный следующий запуск', 'Keyingi ishga tushirish majburiy'))),
                        Switch(
                          value: _cronForceNext,
                          onChanged: _cronBusy ? null : (v) => _saveCronConfig(forceNextRun: v),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton.icon(
                        onPressed: _cronBusy ? null : _runCronTestNow,
                        icon: _cronBusy
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.play_arrow_rounded),
                        label: Text(_t('Запустить тест сейчас', 'Testni hozir ishga tushirish')),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: _loading
                    ? const Center(child: CircularProgressIndicator())
                    : _error != null
                        ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
                        : ListView.separated(
                            itemCount: rows.length,
                            separatorBuilder: (_, __) => const SizedBox(height: 8),
                            itemBuilder: (_, i) {
                              final a = rows[i];
                              final exp = '${a['admin_expires_at'] ?? ''}';
                              return _Card(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Row(
                                      children: [
                                        Expanded(child: Text('${a['id']} ${a['username'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 18))),
                                        Switch(value: a['is_active'] == true, onChanged: (v) => _setActive(a, v)),
                                      ],
                                    ),
                                    Text('Telegram: ${a['telegram_id'] ?? ''}'),
                                    Text('Filiallar: ${_branchNames(a['branches'])}'),
                                    Text('Expiry: ${exp.isEmpty ? '-' : exp.split('T').first}'),
                                    const SizedBox(height: 8),
                                    Wrap(
                                      spacing: 8,
                                      runSpacing: 8,
                                      children: [
                                        OutlinedButton(onPressed: () => _setBranches(a), child: const Text('Filiallar')),
                                        OutlinedButton(onPressed: () => _setExpiry(a), child: const Text('Saqlash')),
                                        OutlinedButton(onPressed: () => _clearExpiry(a), child: const Text('Tozalash')),
                                        OutlinedButton(onPressed: () => _resetPassword(a), child: const Text('Parolni tiklash')),
                                        FilledButton(
                                          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
                                          onPressed: () => _deleteAdmin(a),
                                          child: const Text("O'chirish"),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _NotificationsPage extends StatefulWidget {
  const _NotificationsPage({required this.api, required this.language});

  final _ApiClient api;
  final String language;

  @override
  State<_NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<_NotificationsPage> {
  bool _loading = true;
  String? _error;
  int _unreadCount = 0;
  List<Map<String, dynamic>> _items = [];

  String _t(String ru, String uz) => trPair(ru: ru, uz: uz, lang: widget.language);

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _monthName(int m) {
    if (widget.language == 'ru') {
      const ru = [
        'янв', 'фев', 'мар', 'апр', 'май', 'июн',
        'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'
      ];
      return ru[(m - 1).clamp(0, 11)];
    }
    const uz = [
      'yan', 'fev', 'mar', 'apr', 'may', 'iun',
      'iul', 'avg', 'sen', 'okt', 'noy', 'dek'
    ];
    return uz[(m - 1).clamp(0, 11)];
  }

  String _fmtDate(String raw) {
    if (raw.trim().isEmpty) return '';
    final dt = DateTime.tryParse(raw)?.toLocal();
    if (dt == null) return raw;
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final thatDay = DateTime(dt.year, dt.month, dt.day);
    final diffDays = today.difference(thatDay).inDays;
    final dd = dt.day.toString().padLeft(2, '0');
    final hh = dt.hour.toString().padLeft(2, '0');
    final mm = dt.minute.toString().padLeft(2, '0');
    final timeText = '$hh:$mm';
    if (diffDays == 0) {
      return '${_t('Сегодня', 'Bugun')}, $timeText';
    }
    if (diffDays == 1) {
      return '${_t('Вчера', 'Kecha')}, $timeText';
    }
    return '$dd ${_monthName(dt.month)} ${dt.year}, $timeText';
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await widget.api.getJson('/users/me/notifications', query: const {
        'limit': '100',
        'offset': '0',
      });
      final map = (data as Map).cast<String, dynamic>();
      final list = ((map['items'] as List?) ?? [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList();
      if (!mounted) return;
      setState(() {
        _items = list;
        _unreadCount = ((map['unread_count'] as num?) ?? 0).toInt();
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _markRead(int id) async {
    try {
      await widget.api.postJson('/users/me/notifications/$id/read', {});
    } catch (_) {}
  }

  Future<void> _markAllRead() async {
    try {
      await widget.api.postJson('/users/me/notifications/read-all', {});
      await _load();
    } catch (e) {
      if (!mounted) return;
      showAppAlert(context, '$e', error: true);
    }
  }

  Future<bool> _confirmAction({
    required String title,
    required String message,
    required String yesText,
  }) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: Text(title),
        content: Text(message),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(_t('Отмена', 'Bekor qilish')),
          ),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5534B)),
            onPressed: () => Navigator.pop(context, true),
            child: Text(yesText),
          ),
        ],
      ),
    );
    return result == true;
  }

  Future<void> _deleteOne(int id) async {
    final ok = await _confirmAction(
      title: _t('Удалить уведомление?', "Bildirishnomani o'chirish?"),
      message: _t(
        'Это действие нельзя отменить.',
        "Bu amalni ortga qaytarib bo'lmaydi.",
      ),
      yesText: _t('Удалить', "O'chirish"),
    );
    if (!ok) return;
    try {
      await widget.api.deleteJson('/users/me/notifications/$id');
      await _load();
    } catch (e) {
      if (!mounted) return;
      showAppAlert(context, '$e', error: true);
    }
  }

  Future<void> _deleteRead() async {
    final ok = await _confirmAction(
      title: _t('Удалить прочитанные?', "O'qilganlarni o'chirish?"),
      message: _t(
        'Будут удалены все прочитанные уведомления.',
        "Barcha o'qilgan bildirishnomalar o'chiriladi.",
      ),
      yesText: _t('Удалить', "O'chirish"),
    );
    if (!ok) return;
    try {
      await widget.api.deleteJson('/users/me/notifications/read');
      await _load();
    } catch (e) {
      if (!mounted) return;
      showAppAlert(context, '$e', error: true);
    }
  }

  Future<void> _deleteAll() async {
    final ok = await _confirmAction(
      title: _t('Удалить все уведомления?', "Barcha bildirishnomalarni o'chirish?"),
      message: _t(
        'Будут удалены все уведомления, включая новые.',
        "Barcha bildirishnomalar, shu jumladan yangilari ham o'chiriladi.",
      ),
      yesText: _t('Удалить все', "Hammasini o'chirish"),
    );
    if (!ok) return;
    try {
      await widget.api.deleteJson('/users/me/notifications');
      await _load();
    } catch (e) {
      if (!mounted) return;
      showAppAlert(context, '$e', error: true);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${_t('Уведомления', 'Bildirishnomalar')} ($_unreadCount)'),
        actions: [
          TextButton.icon(
            onPressed: _loading || _items.isEmpty ? null : _markAllRead,
            icon: const Icon(Icons.done_all_rounded, size: 18),
            label: Text(_t('Прочитать все', "Barchasini o'qish")),
          ),
          PopupMenuButton<String>(
            onSelected: (value) {
              if (value == 'delete_read') {
                _deleteRead();
              } else if (value == 'delete_all') {
                _deleteAll();
              }
            },
            itemBuilder: (_) => [
              PopupMenuItem(
                value: 'delete_read',
                child: Text(_t('Удалить прочитанные', "O'qilganlarni o'chirish")),
              ),
              PopupMenuItem(
                value: 'delete_all',
                child: Text(_t('Удалить все', "Hammasini o'chirish")),
              ),
            ],
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!, style: const TextStyle(color: Colors.red)))
              : _items.isEmpty
                  ? Center(child: Text(_t('Уведомлений пока нет', "Hozircha bildirishnoma yo'q")))
                  : ListView.separated(
                      padding: const EdgeInsets.all(12),
                      itemCount: _items.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 8),
                      itemBuilder: (_, i) {
                        final n = _items[i];
                        final id = (n['id'] as num?)?.toInt() ?? 0;
                        final isRead = n['is_read'] == true;
                        final title = '${n['title'] ?? ''}';
                        final body = '${n['body'] ?? ''}';
                        final created = _fmtDate('${n['created_at'] ?? ''}');

                        return InkWell(
                          borderRadius: BorderRadius.circular(16),
                          onTap: () async {
                            if (!isRead && id > 0) {
                              await _markRead(id);
                              await _load();
                            }
                          },
                          child: Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: isRead ? Colors.white : const Color(0xFFF0F9FF),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: isRead ? const Color(0xFFE5E7EB) : const Color(0xFF7DD3FC),
                              ),
                            ),
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Icon(
                                  isRead ? Icons.mark_email_read_outlined : Icons.mark_email_unread_outlined,
                                  color: isRead ? const Color(0xFF64748B) : const Color(0xFF2563EB),
                                ),
                                const SizedBox(width: 10),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Row(
                                        children: [
                                          Expanded(
                                            child: Text(
                                              title,
                                              maxLines: 2,
                                              overflow: TextOverflow.ellipsis,
                                              style: TextStyle(
                                                fontWeight: isRead ? FontWeight.w600 : FontWeight.w800,
                                                fontSize: 15,
                                              ),
                                            ),
                                          ),
                                          if (!isRead)
                                            Container(
                                              margin: const EdgeInsets.only(left: 8),
                                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                                              decoration: BoxDecoration(
                                                color: const Color(0xFFDBEAFE),
                                                borderRadius: BorderRadius.circular(999),
                                              ),
                                              child: Text(
                                                _t('Новое', 'Yangi'),
                                                style: const TextStyle(
                                                  fontSize: 11,
                                                  fontWeight: FontWeight.w700,
                                                  color: Color(0xFF1D4ED8),
                                                ),
                                              ),
                                            ),
                                        ],
                                      ),
                                      const SizedBox(height: 4),
                                      Text(
                                        body,
                                        style: const TextStyle(height: 1.3),
                                      ),
                                      if (created.isNotEmpty) ...[
                                        const SizedBox(height: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                          decoration: BoxDecoration(
                                            color: const Color(0xFFF8FAFC),
                                            borderRadius: BorderRadius.circular(8),
                                          ),
                                          child: Text(
                                            created,
                                            style: const TextStyle(
                                              fontSize: 12,
                                              color: Color(0xFF6B7280),
                                            ),
                                          ),
                                        ),
                                      ]
                                    ],
                                  ),
                                ),
                                const SizedBox(width: 6),
                                IconButton(
                                  tooltip: _t('Удалить', "O'chirish"),
                                  onPressed: id > 0 ? () => _deleteOne(id) : null,
                                  icon: const Icon(Icons.delete_outline_rounded),
                                  color: const Color(0xFFDC2626),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
    );
  }
}

class _ErrorText extends StatelessWidget {
  const _ErrorText({required this.error});
  final String error;
  @override
  Widget build(BuildContext context) {
    final message = friendlyErrorText(error);
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: const Color(0xFFFFF1F2),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: const Color(0xFFFECACA)),
          ),
          child: Text(
            '⚠ $message',
            textAlign: TextAlign.center,
            style: const TextStyle(
              color: Color(0xFFB91C1C),
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
    );
  }
}

class _WebIcon extends StatelessWidget {
  const _WebIcon(this.name, {this.size = 20});
  final String name;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Image.asset(
      'assets/icons/$name.png',
      width: size,
      height: size,
      fit: BoxFit.contain,
      errorBuilder: (_, __, ___) => Icon(Icons.image_not_supported_outlined, size: size),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle(this.text);
  final String text;
  @override
  Widget build(BuildContext context) {
    return Text(text, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800, letterSpacing: 0.2));
  }
}

class _Card extends StatelessWidget {
  const _Card({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(18),
        boxShadow: const [BoxShadow(color: Color(0x11000000), blurRadius: 12, offset: Offset(0, 4))],
      ),
      child: child,
    );
  }
}

class _StatChip extends StatelessWidget {
  const _StatChip({required this.label, required this.value, required this.color});
  final String label;
  final String value;
  final Color color;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(color: color.withOpacity(0.18), borderRadius: BorderRadius.circular(16)),
      child: Column(
        children: [
          Text(label, style: TextStyle(color: color, fontWeight: FontWeight.w600)),
          Text(value, style: TextStyle(color: color, fontSize: 20, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _NumberBox extends StatelessWidget {
  const _NumberBox({required this.title, required this.value, required this.bg});
  final String title;
  final String value;
  final Color bg;
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(16)),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(color: Colors.black54)),
          const SizedBox(height: 6),
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
        ],
      ),
    );
  }
}

class _FakeInput extends StatelessWidget {
  const _FakeInput(this.hint);
  final String hint;
  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFD1D5DB)),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Text(hint, style: const TextStyle(color: Colors.black45, fontSize: 14)),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState(this.message);
  final String message;
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: _Card(
        child: Row(
          children: [
            const Icon(Icons.info_outline, color: Color(0xFF64748B)),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(color: Color(0xFF475467), fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
