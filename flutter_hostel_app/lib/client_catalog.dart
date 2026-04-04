import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:geolocator/geolocator.dart' as geo;
import 'package:http/http.dart' as http;
import 'package:latlong2/latlong.dart';
import 'package:mapbox_maps_flutter/mapbox_maps_flutter.dart' as mb;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import 'main.dart';

const String _publicApiBase = 'https://hmsuz.com/public-api';
const String _publicHost = 'https://hmsuz.com';
const String _clientLastContactKey = 'client_last_contact';
String _mapboxToken() => dotenv.get('MAPBOX_TOKEN', fallback: '');

const Color _bg = Color(0xFFF5F7FB);
const Color _card = Color(0xFFFFFFFF);
const Color _textMuted = Color(0xFF64748B);
const Color _border = Color(0xFFE2E8F0);
const Color _brandBlue = Color(0xFF1D4ED8);
const Color _surfaceSoft = Color(0xFFF7F9FC);

List<String> _parseAmenities(String? raw, {int max = 8}) {
  final text = (raw ?? '').trim();
  if (text.isEmpty) return const [];
  final parts = text.split(RegExp(r'[;,/|]'));
  final out = <String>[];
  for (final p in parts) {
    final v = p.trim();
    if (v.isEmpty) continue;
    if (!out.contains(v)) out.add(v);
    if (out.length >= max) break;
  }
  return out;
}

const List<Map<String, String>> _regionOptions = [
  {'slug': 'andizhanskaya-oblast', 'ru': 'Андижанская область', 'uz': 'Andijon viloyati'},
  {'slug': 'buharskaya-oblast', 'ru': 'Бухарская область', 'uz': 'Buxoro viloyati'},
  {'slug': 'dzhizakskaya-oblast', 'ru': 'Джизакская область', 'uz': 'Jizzax viloyati'},
  {'slug': 'karakalpakstan', 'ru': 'Каракалпакстан', 'uz': 'Qoraqalpog‘iston'},
  {'slug': 'kashkadarinskaya-oblast', 'ru': 'Кашкадарьинская область', 'uz': 'Qashqadaryo viloyati'},
  {'slug': 'navoijskaya-oblast', 'ru': 'Навоийская область', 'uz': 'Navoiy viloyati'},
  {'slug': 'namanganskaya-oblast', 'ru': 'Наманганская область', 'uz': 'Namangan viloyati'},
  {'slug': 'samarkandskaya-oblast', 'ru': 'Самаркандская область', 'uz': 'Samarqand viloyati'},
  {'slug': 'surhandarinskaya-oblast', 'ru': 'Сурхандарьинская область', 'uz': 'Surxondaryo viloyati'},
  {'slug': 'syrdarinskaya-oblast', 'ru': 'Сырдарьинская область', 'uz': 'Sirdaryo viloyati'},
  {'slug': 'toshkent-oblast', 'ru': 'Ташкентская область', 'uz': 'Toshkent viloyati'},
  {'slug': 'ferganskaya-oblast', 'ru': 'Ферганская область', 'uz': 'Farg‘ona viloyati'},
  {'slug': 'horezmskaya-oblast', 'ru': 'Хорезмская область', 'uz': 'Xorazm viloyati'},
];

class ClientCatalogScreen extends StatefulWidget {
  const ClientCatalogScreen({super.key, required this.lang});

  final String lang;

  @override
  State<ClientCatalogScreen> createState() => _ClientCatalogScreenState();
}

class _ClientCatalogScreenState extends State<ClientCatalogScreen> {
  final _searchCtrl = TextEditingController();
  final _regionCtrl = TextEditingController();
  final _cityCtrl = TextEditingController();
  final _districtCtrl = TextEditingController();
  final _roomTypeCtrl = TextEditingController();
  bool _loading = false;
  bool _filtersOpen = false;
  bool _filtersActive = false;
  bool _filtersOpening = false;
  int _page = 1;
  static const int _pageSize = 12;
  int _totalCount = 0;
  String _priceMode = 'day';
  double _minRating = 0;
  double? _distanceKm;
  LatLng? _catalogUserPos;
  String? _regionSlug;
  String? _cityName;
  String? _districtName;
  String? _roomType;
  RangeValues _priceRange = const RangeValues(0, 0);
  bool _priceRangeDirty = false;
  double _priceMinBound = 0;
  double _priceMaxBound = 0;
  List<BranchSummary> _branches = [];
  List<BranchSummary> _filtered = [];
  Map<String, List<String>> _regionCities = {};
  Map<String, List<String>> _cityDistricts = {};
  late String _lang;
  final Map<int, String> _cardTabs = {};
  Timer? _reloadTimer;

  @override
  void initState() {
    super.initState();
    _lang = widget.lang;
    _loadRegionCityAsset();
    _loadAll();
    _searchCtrl.addListener(_applyClientFilters);
  }

  @override
  void dispose() {
    _reloadTimer?.cancel();
    _searchCtrl.dispose();
    _regionCtrl.dispose();
    _cityCtrl.dispose();
    _districtCtrl.dispose();
    _roomTypeCtrl.dispose();
    super.dispose();
  }

  String _tr({required String ru, required String uz}) {
    return _lang == 'ru' ? ru : uz;
  }

  Widget _dropdownPlaceholder(String text) {
    return Text(text, style: const TextStyle(fontSize: 12, color: _textMuted));
  }

  void _setLang(String lang) {
    setState(() {
      _lang = lang == 'ru' ? 'ru' : 'uz';
    });
  }

  Future<void> _setLangAndSave(String lang) async {
    _setLang(lang);
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('language', _lang);
    } catch (_) {}
  }

  void _openLangPicker() async {
    final chosen = await showMenu<String>(
      context: context,
      position: const RelativeRect.fromLTRB(1000, 80, 16, 0),
      items: [
        CheckedPopupMenuItem(value: 'ru', checked: _lang == 'ru', child: const Text('RU')),
        CheckedPopupMenuItem(value: 'uz', checked: _lang == 'uz', child: const Text('UZ')),
      ],
    );
    if (chosen != null) {
      _setLangAndSave(chosen);
    }
  }

  Future<void> _openProfileMenu() async {
    final selected = await showMenu<String>(
      context: context,
      position: const RelativeRect.fromLTRB(1000, 80, 8, 0),
      items: [
        PopupMenuItem(value: 'account', child: Text(_tr(ru: 'Мой аккаунт', uz: 'Mening akkauntim'))),
        PopupMenuItem(value: 'bookings', child: Text(_tr(ru: 'Мои брони', uz: 'Mening bronlarim'))),
        PopupMenuItem(value: 'feedbacks', child: Text(_tr(ru: 'Мои отзывы', uz: 'Fikrlarim'))),
        PopupMenuItem(value: 'settings', child: Text(_tr(ru: 'Настройки', uz: 'Sozlamalar'))),
        PopupMenuItem(value: 'themes', child: Text(_tr(ru: 'Темы', uz: 'Temalar'))),
        const PopupMenuDivider(),
        PopupMenuItem(value: 'logout', child: Text(_tr(ru: 'Выйти', uz: 'Chiqish'))),
      ],
    );
    if (selected == null) return;
    switch (selected) {
      case 'account':
        await _openWebPath('/catalog/my-account');
        break;
      case 'bookings':
        await _openWebPath('/catalog/booking-history');
        break;
      case 'feedbacks':
        await _openWebPath('/catalog/feedbacks');
        break;
      case 'settings':
        await _openWebPath('/catalog/settings');
        break;
      case 'themes':
        await _openWebPath('/catalog/settings#themes');
        break;
      case 'logout':
        await _logoutToLogin();
        break;
    }
  }

  Future<void> _openWebPath(String path) async {
    final clean = path.startsWith('/') ? path : '/$path';
    final uri = Uri.parse('$_publicHost$clean?lang=$_lang');
    await launchUrl(uri, mode: LaunchMode.inAppBrowserView);
  }

  Future<void> _logoutToLogin() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('access_token');
      await prefs.remove('branch_id');
      await prefs.remove('user_id');
      await prefs.remove('is_admin');
    } catch (_) {}
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const LoginScreen()),
    );
  }

  Future<void> _loadAll() async {
    await _loadBranches();
  }

  Future<void> _loadBranches() async {
    setState(() => _loading = true);
    try {
      final q = <String, String>{
        'limit': '$_pageSize',
        'offset': '${(_page - 1) * _pageSize}',
        'price_mode': _priceMode,
        'include_total': '1',
        'include_bounds': '1',
      };
      if (_minRating > 0) q['min_rating'] = _minRating.toStringAsFixed(1);
      if (_roomType != null && _roomType!.trim().isNotEmpty) q['room_type'] = _roomType!;
      if (_regionSlug != null && _regionSlug!.trim().isNotEmpty) q['region_slug'] = _regionSlug!;
      if (_cityName != null && _cityName!.trim().isNotEmpty) q['city_name'] = _cityName!;
      if (_districtName != null && _districtName!.trim().isNotEmpty) q['district_name'] = _districtName!;
      final search = _searchCtrl.text.trim();
      if (search.isNotEmpty) q['q'] = search;
      if (_priceRangeDirty) {
        q['min_price'] = _priceRange.start.toStringAsFixed(0);
        q['max_price'] = _priceRange.end.toStringAsFixed(0);
      }
      if (_distanceKm != null && _catalogUserPos != null) {
        q['lat'] = _catalogUserPos!.latitude.toStringAsFixed(6);
        q['lng'] = _catalogUserPos!.longitude.toStringAsFixed(6);
        q['radius_km'] = _distanceKm!.toStringAsFixed(2);
      }
      final uri = Uri.parse('$_publicApiBase/branches').replace(queryParameters: q);
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode != 200) {
        _showSnack(_tr(ru: 'Не удалось загрузить каталог.', uz: 'Katalogni yuklab bo\'lmadi.'), error: true);
        return;
      }
      final data = jsonDecode(res.body);
      List listRaw;
      int total = 0;
      if (data is Map<String, dynamic>) {
        listRaw = (data['items'] as List?) ?? [];
        total = (data['total'] as num?)?.toInt() ?? 0;
        final bounds = data['bounds'];
        if (bounds is Map) {
          final bmin = double.tryParse('${bounds['min'] ?? ''}');
          final bmax = double.tryParse('${bounds['max'] ?? ''}');
          if (bmin != null && bmax != null) {
            _priceMinBound = bmin.floorToDouble();
            _priceMaxBound = bmax.ceilToDouble();
            if (_priceMaxBound < _priceMinBound) {
              _priceMaxBound = _priceMinBound;
            }
            if (!_priceRangeDirty) {
              _priceRange = RangeValues(_priceMinBound, _priceMaxBound);
            }
          }
        }
      } else if (data is List) {
        listRaw = data;
        total = listRaw.length;
      } else {
        listRaw = [];
      }
      final list = listRaw.map((e) => BranchSummary.fromJson(e as Map<String, dynamic>)).toList();
      _branches = list;
      _filtered = list;
      _totalCount = total;
      _recomputePriceBounds();
    } catch (e) {
      _showSnack(_friendlyError(e.toString()), error: true);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _recomputePriceBounds() {
    double? minV;
    double? maxV;
    for (final b in _branches) {
      if (b.minPrice != null) {
        minV = minV == null ? b.minPrice : (b.minPrice! < minV ? b.minPrice : minV);
        maxV = maxV == null ? b.minPrice : (b.minPrice! > maxV ? b.minPrice : maxV);
      }
      if (b.maxPrice != null) {
        minV = minV == null ? b.maxPrice : (b.maxPrice! < minV ? b.maxPrice : minV);
        maxV = maxV == null ? b.maxPrice : (b.maxPrice! > maxV ? b.maxPrice : maxV);
      }
    }
    _priceMinBound = (minV ?? 0).floorToDouble();
    _priceMaxBound = (maxV ?? 0).ceilToDouble();
    if (_priceMaxBound < _priceMinBound) {
      _priceMaxBound = _priceMinBound;
    }
    if (!_priceRangeDirty) {
      _priceRange = RangeValues(_priceMinBound, _priceMaxBound);
    }
  }

  void _applyClientFilters() {
    _reloadTimer?.cancel();
    setState(() {
      _filtersActive = _hasActiveFilters(includeSearch: false);
      _page = 1;
    });
    _reloadTimer = Timer(const Duration(milliseconds: 250), () {
      _loadBranches();
    });
  }

  void _toggleFilters() {
    if (_filtersOpen) {
      setState(() {
        _filtersOpen = false;
        _filtersOpening = false;
      });
      return;
    }
    setState(() => _filtersOpening = true);
    Future.delayed(const Duration(milliseconds: 180), () {
      if (!mounted) return;
      setState(() {
        _filtersOpen = true;
        _filtersOpening = false;
      });
    });
  }

  bool _hasActiveFilters({bool includeSearch = true}) {
    if (includeSearch && _searchCtrl.text.trim().isNotEmpty) return true;
    if (_regionSlug != null && _regionSlug!.trim().isNotEmpty) return true;
    if (_cityName != null && _cityName!.trim().isNotEmpty) return true;
    if (_districtName != null && _districtName!.trim().isNotEmpty) return true;
    if (_roomType != null && _roomType!.trim().isNotEmpty) return true;
    if (_priceMode != 'day') return true;
    if (_priceRangeDirty) return true;
    if (_minRating > 0) return true;
    if (_distanceKm != null) return true;
    return false;
  }

  void _resetFilters() {
    setState(() {
      _searchCtrl.clear();
      _regionCtrl.clear();
      _cityCtrl.clear();
      _districtCtrl.clear();
      _roomTypeCtrl.clear();
      _priceMode = 'day';
      _minRating = 0;
      _regionSlug = null;
      _cityName = null;
      _districtName = null;
      _roomType = null;
      _priceRange = RangeValues(_priceMinBound, _priceMaxBound);
      _priceRangeDirty = false;
      _distanceKm = null;
      _filtersActive = false;
      _page = 1;
    });
    _applyClientFilters();
  }

  Future<bool> _ensureCatalogLocation() async {
    try {
      final serviceEnabled = await geo.Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        await geo.Geolocator.openLocationSettings();
        return false;
      }
      var permission = await geo.Geolocator.checkPermission();
      if (permission == geo.LocationPermission.denied) {
        permission = await geo.Geolocator.requestPermission();
      }
      if (permission == geo.LocationPermission.denied || permission == geo.LocationPermission.deniedForever) {
        return false;
      }
      final pos = await geo.Geolocator.getCurrentPosition(
        desiredAccuracy: geo.LocationAccuracy.high,
        timeLimit: const Duration(seconds: 8),
      );
      if (!mounted) return false;
      setState(() => _catalogUserPos = LatLng(pos.latitude, pos.longitude));
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<void> _setDistanceFilter(double? km) async {
    if (km == null) {
      setState(() => _distanceKm = null);
      _applyClientFilters();
      return;
    }
    if (_catalogUserPos == null) {
      final ok = await _ensureCatalogLocation();
      if (!ok) {
        if (mounted) {
          _showSnack(_tr(ru: 'Сначала включите GPS.', uz: 'Avval GPS ni yoqing.'), error: true);
        }
        return;
      }
    }
    setState(() => _distanceKm = km);
    _applyClientFilters();
  }

  List<DropdownMenuItem<String?>> _regionItems() {
    final items = _regionOptions
        .map((e) => MapEntry(e['slug']!, _lang == 'ru' ? e['ru']! : e['uz']!))
        .toList()
      ..sort((a, b) => a.value.compareTo(b.value));
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все области', uz: 'Barcha viloyatlar'))),
      ...items.map((e) => DropdownMenuItem<String?>(value: e.key, child: Text(e.value))),
    ];
  }

  Future<void> _loadRegionCityAsset() async {
    try {
      final raw = await rootBundle.loadString('assets/uz_regions_cities.json');
      final data = jsonDecode(raw);
      if (data is! Map) return;
      final rc = data['regions_cities'];
      final cd = data['city_districts'];
      Map<String, List<String>> toMap(dynamic input) {
        final out = <String, List<String>>{};
        if (input is! Map) return out;
        for (final entry in input.entries) {
          final key = '${entry.key}'.trim();
          if (key.isEmpty) continue;
          final list = <String>[];
          if (entry.value is List) {
            for (final v in entry.value as List) {
              final text = '${v ?? ''}'.trim();
              if (text.isNotEmpty) list.add(text);
            }
          }
          out[key] = list;
        }
        return out;
      }

      final regionsCities = toMap(rc);
      final cityDistricts = toMap(cd);
      if (!mounted) return;
      setState(() {
        _regionCities = regionsCities;
        _cityDistricts = cityDistricts;
      });
    } catch (_) {}
  }

  List<String> _regionNames() {
    final names = _regionOptions
        .map((e) => _lang == 'ru' ? e['ru']! : e['uz']!)
        .toList()
      ..sort();
    return names;
  }

  String? _regionSlugByName(String name) {
    for (final e in _regionOptions) {
      final text = _lang == 'ru' ? e['ru']! : e['uz']!;
      if (text == name) return e['slug'];
    }
    return null;
  }

  List<DropdownMenuItem<String?>> _cityItems() {
    List<String> list = [];
    if (_regionCities.isNotEmpty) {
      if (_regionSlug != null && _regionSlug!.isNotEmpty && _regionCities.containsKey(_regionSlug)) {
        list = List<String>.from(_regionCities[_regionSlug] ?? const []);
      } else {
        final set = <String>{};
        for (final cities in _regionCities.values) {
          set.addAll(cities);
        }
        list = set.toList();
      }
    } else {
      final set = <String>{};
      for (final b in _branches) {
        if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
        final name = (b.cityName ?? '').trim();
        if (name.isNotEmpty) set.add(name);
      }
      list = set.toList();
    }
    list.sort();
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все города', uz: 'Barcha shaharlar'))),
      ...list.map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
    ];
  }

  List<String> _cityNames() {
    List<String> list = [];
    if (_regionCities.isNotEmpty) {
      if (_regionSlug != null && _regionSlug!.isNotEmpty && _regionCities.containsKey(_regionSlug)) {
        list = List<String>.from(_regionCities[_regionSlug] ?? const []);
      } else {
        final set = <String>{};
        for (final cities in _regionCities.values) {
          set.addAll(cities);
        }
        list = set.toList();
      }
    } else {
      final set = <String>{};
      for (final b in _branches) {
        if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
        final name = (b.cityName ?? '').trim();
        if (name.isNotEmpty) set.add(name);
      }
      list = set.toList();
    }
    list.sort();
    return list;
  }

  List<DropdownMenuItem<String?>> _districtItems() {
    List<String> list = [];
    if (_cityDistricts.isNotEmpty && _cityName != null && _cityName!.isNotEmpty && _cityDistricts.containsKey(_cityName)) {
      list = List<String>.from(_cityDistricts[_cityName] ?? const []);
    } else {
      final set = <String>{};
      for (final b in _branches) {
        if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
        if (_cityName != null && _cityName!.isNotEmpty && b.cityName != _cityName) continue;
        final name = (b.districtName ?? '').trim();
        if (name.isNotEmpty) set.add(name);
      }
      list = set.toList();
    }
    list.sort();
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все районы', uz: 'Barcha tumanlar'))),
      ...list.map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
    ];
  }

  List<String> _districtNames() {
    List<String> list = [];
    if (_cityDistricts.isNotEmpty && _cityName != null && _cityName!.isNotEmpty && _cityDistricts.containsKey(_cityName)) {
      list = List<String>.from(_cityDistricts[_cityName] ?? const []);
    } else {
      final set = <String>{};
      for (final b in _branches) {
        if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
        if (_cityName != null && _cityName!.isNotEmpty && b.cityName != _cityName) continue;
        final name = (b.districtName ?? '').trim();
        if (name.isNotEmpty) set.add(name);
      }
      list = set.toList();
    }
    list.sort();
    return list;
  }

  List<DropdownMenuItem<String?>> _roomTypeItems() {
    final set = <String>{};
    for (final b in _branches) {
      final parts = b.roomTypes.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty);
      set.addAll(parts);
    }
    final list = set.toList()..sort();
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все типы', uz: 'Barcha turlar'))),
      ...list.map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
    ];
  }

  List<String> _roomTypeNames() {
    final set = <String>{};
    for (final b in _branches) {
      final parts = b.roomTypes.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty);
      set.addAll(parts);
    }
    final list = set.toList()..sort();
    return list;
  }

  Future<void> _openHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final lastContact = prefs.getString(_clientLastContactKey) ?? '';
    final contactCtrl = TextEditingController(text: lastContact);
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) {
        return AlertDialog(
          title: Text(_tr(ru: 'История', uz: 'Tarix')),
          content: TextField(
            controller: contactCtrl,
            keyboardType: TextInputType.phone,
            decoration: InputDecoration(
              labelText: _tr(ru: 'Телефон', uz: 'Telefon'),
              hintText: '+998...'
            ),
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_tr(ru: 'Отмена', uz: 'Bekor'))),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_tr(ru: 'Показать', uz: "Ko'rsatish"))),
          ],
        );
      },
    );
    if (ok != true) return;
    final contact = contactCtrl.text.trim();
    if (contact.isEmpty) {
      _showSnack(_tr(ru: 'Введите телефон.', uz: 'Telefon kiriting.'), error: true);
      return;
    }
    await prefs.setString(_clientLastContactKey, contact);
    final historyContact = contact;
    await showDialog<void>(
      context: context,
      builder: (_) => FutureBuilder<List<UserHistoryItem>>(
        future: _fetchHistory(contact),
        builder: (context, snap) {
          final items = snap.data ?? [];
          return AlertDialog(
            backgroundColor: _card,
            title: Text(_tr(ru: 'История', uz: 'Tarix')),
            content: SizedBox(
              width: double.maxFinite,
              child: snap.connectionState != ConnectionState.done
                  ? const Center(child: CircularProgressIndicator())
                  : items.isEmpty
                      ? Text(_tr(ru: 'История не найдена.', uz: 'Tarix topilmadi.'))
                      : ListView.separated(
                          shrinkWrap: true,
                          itemCount: items.length,
                          separatorBuilder: (_, __) => const Divider(height: 16, color: _border),
                          itemBuilder: (_, i) {
                            final it = items[i];
                            return Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(it.branchName, style: const TextStyle(fontWeight: FontWeight.w700)),
                                const SizedBox(height: 4),
                                Text(it.message, style: const TextStyle(color: _textMuted)),
                                const SizedBox(height: 6),
                                Row(
                                  children: [
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                                      decoration: BoxDecoration(
                                        color: const Color(0xFFF1F5F9),
                                        borderRadius: BorderRadius.circular(8),
                                        border: Border.all(color: _border),
                                      ),
                                      child: Text(it.itemTypeLabel(_lang), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600)),
                                    ),
                                    const Spacer(),
                                    if (it.itemType == 'booking')
                                      OutlinedButton(
                                        style: OutlinedButton.styleFrom(
                                          foregroundColor: _brandBlue,
                                          side: const BorderSide(color: _border),
                                        ),
                                        onPressed: () => _submitRatingFromHistory(it.branchId, historyContact),
                                        child: Text(_tr(ru: 'Оценить', uz: 'Baho berish')),
                                      ),
                                  ],
                                ),
                              ],
                            );
                          },
                        ),
            ),
          );
        },
      ),
    );
  }

  Future<List<UserHistoryItem>> _fetchHistory(String contact) async {
    try {
      final uri = Uri.parse('$_publicApiBase/user-history').replace(queryParameters: {
        'contact': contact,
      });
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode != 200) return [];
      final payload = jsonDecode(res.body);
      final items = payload is Map<String, dynamic> ? payload['items'] : payload;
      if (items is List) {
        return items
            .whereType<Map<String, dynamic>>()
            .map((e) => UserHistoryItem.fromJson(e))
            .toList();
      }
      return [];
    } catch (_) {
      return [];
    }
  }

  Future<void> _submitRatingFromHistory(int branchId, String contact) async {
    if (!mounted) return;
    final ratingCtrl = TextEditingController(text: '5');
    final commentCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) {
        return AlertDialog(
          title: Text(_tr(ru: 'Оценить', uz: 'Baho berish')),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                controller: ratingCtrl,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: _tr(ru: 'Оценка 1-5', uz: 'Baho 1-5'),
                ),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: commentCtrl,
                decoration: InputDecoration(
                  labelText: _tr(ru: 'Комментарий (необязательно)', uz: 'Izoh (ixtiyoriy)'),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_tr(ru: 'Отмена', uz: 'Bekor'))),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_tr(ru: 'Отправить', uz: 'Yuborish'))),
          ],
        );
      },
    );
    if (ok != true) return;
    final rating = int.tryParse(ratingCtrl.text.trim()) ?? 0;
    final value = rating.clamp(1, 5);
    final comment = commentCtrl.text.trim();
    try {
      final uri = Uri.parse('$_publicApiBase/branches/$branchId/ratings');
      final payload = {
        'rating': value,
        'comment': comment,
        'contact': contact,
        'source': 'mobile_app',
      };
      final res = await http.post(
        uri,
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );
      if (res.statusCode == 403) {
        _showSnack(_tr(ru: 'Оценка доступна после выезда.', uz: 'Baho faqat chiqishdan keyin mumkin.'), error: true);
        return;
      }
      if (res.statusCode < 200 || res.statusCode >= 300) {
        _showSnack(_tr(ru: 'Не удалось сохранить оценку.', uz: 'Bahoni saqlab bo\'lmadi.'), error: true);
        return;
      }
      _showSnack(_tr(ru: 'Оценка сохранена.', uz: 'Baho saqlandi.'));
    } catch (e) {
      _showSnack(_friendlyError(e.toString()), error: true);
    }
  }

  void _showSnack(String msg, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: error ? const Color(0xFFDC2626) : const Color(0xFF1D4ED8),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }

  double? _distanceKmBetween(LatLng from, double lat, double lon) {
    try {
      final distance = Distance();
      return distance.as(LengthUnit.Kilometer, from, LatLng(lat, lon));
    } catch (_) {
      return null;
    }
  }

  String? _normalizePhoto(dynamic v) {
    if (v == null) return null;
    final raw = v.toString();
    if (raw.isEmpty) return null;
    if (raw.startsWith('//')) return 'https:$raw';
    if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
    if (raw.startsWith('/')) return '$_publicHost$raw';
    return '$_publicHost/$raw';
  }

  Future<List<String>> _fetchBranchPhotos(int branchId) async {
    try {
      final uri = Uri.parse('$_publicApiBase/branches/$branchId/photos')
          .replace(queryParameters: const {'limit': '80'});
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode != 200) return const [];
      final payload = jsonDecode(res.body);
      final items = payload is Map<String, dynamic>
          ? (payload['items'] ?? payload['photos'] ?? payload['data'] ?? [])
          : payload;
      if (items is! List) return const [];
      final out = <String>[];
      for (final item in items) {
        String? url;
        if (item is Map) {
          url = _normalizePhoto(item['image_path'] ?? item['url'] ?? item['photo'] ?? item['image']);
        } else {
          url = _normalizePhoto(item);
        }
        if (url != null && url.isNotEmpty) out.add(url);
      }
      final unique = <String>[];
      for (final u in out) {
        if (!unique.contains(u)) unique.add(u);
      }
      if (unique.isNotEmpty) return unique;
      // Fallback: try details endpoint (some servers return photos there)
      final detailsUri = Uri.parse('$_publicApiBase/branches/$branchId/details')
          .replace(queryParameters: {'price_mode': _priceMode});
      final detailsRes = await http.get(detailsUri, headers: const {'Cache-Control': 'no-cache'});
      if (detailsRes.statusCode != 200) return const [];
      final detailsPayload = jsonDecode(detailsRes.body);
      final branch = (detailsPayload is Map<String, dynamic>)
          ? (detailsPayload['branch'] ?? detailsPayload)
          : detailsPayload;
      final fallback = <String>[];
      void collect(dynamic v) {
        if (v is List) {
          for (final x in v) collect(x);
        } else if (v is Map) {
          final url = _normalizePhoto(v['image_path'] ?? v['url'] ?? v['photo'] ?? v['image']);
          if (url != null && url.isNotEmpty) fallback.add(url);
          for (final key in ['photos', 'images', 'gallery', 'files', 'media']) {
            if (v.containsKey(key)) collect(v[key]);
          }
          if (v.containsKey('cover_image')) collect(v['cover_image']);
          if (v.containsKey('cover_photo')) collect(v['cover_photo']);
        } else {
          final url = _normalizePhoto(v);
          if (url != null && url.isNotEmpty) fallback.add(url);
        }
      }
      collect(branch);
      final uniqueFallback = <String>[];
      for (final u in fallback) {
        if (!uniqueFallback.contains(u)) uniqueFallback.add(u);
      }
      return uniqueFallback;
    } catch (_) {
      return const [];
    }
  }

  Future<void> _openBranchGallery(BranchSummary b) async {
    if (!mounted) return;
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(child: CircularProgressIndicator()),
    );
    var photos = await _fetchBranchPhotos(b.id);
    if (mounted) Navigator.of(context).pop();
    if (photos.isEmpty && b.coverPhoto != null && b.coverPhoto!.trim().isNotEmpty) {
      photos = [b.coverPhoto!];
    }
    if (photos.isEmpty) {
      _showSnack(_tr(ru: 'Фото не найдено.', uz: 'Rasm topilmadi.'));
      return;
    }
    _openImageGallery(photos, 0);
  }

  void _openImageGallery(List<String> photos, int initialIndex) {
    if (photos.isEmpty) return;
    final start = initialIndex.clamp(0, photos.length - 1);
    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.85),
      builder: (_) {
        int index = start;
        final controller = PageController(initialPage: start);
        return StatefulBuilder(
          builder: (context, setState) => Material(
            color: Colors.transparent,
            child: Stack(
              children: [
                Positioned.fill(
                  child: Column(
                    children: [
                      Expanded(
                        child: PageView.builder(
                          controller: controller,
                          itemCount: photos.length,
                          onPageChanged: (i) => setState(() => index = i),
                          itemBuilder: (_, i) => InteractiveViewer(
                            minScale: 0.8,
                            maxScale: 4,
                            child: Center(
                              child: Image.network(
                                photos[i],
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) => const Icon(
                                  Icons.image_not_supported_outlined,
                                  color: Colors.white70,
                                  size: 48,
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      if (photos.length > 1)
                        Container(
                          padding: const EdgeInsets.fromLTRB(12, 8, 12, 18),
                          height: 90,
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: photos.length,
                            separatorBuilder: (_, __) => const SizedBox(width: 8),
                            itemBuilder: (_, i) => GestureDetector(
                              onTap: () {
                                controller.jumpToPage(i);
                                setState(() => index = i);
                              },
                              child: Container(
                                width: 88,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(10),
                                  border: Border.all(
                                    color: i == index ? const Color(0xFFF97316) : Colors.white24,
                                    width: 2,
                                  ),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(8),
                                  child: Image.network(
                                    photos[i],
                                    fit: BoxFit.cover,
                                    errorBuilder: (_, __, ___) => const ColoredBox(
                                      color: Color(0xFF1F2937),
                                      child: Icon(Icons.broken_image, color: Colors.white70),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                Positioned(
                  top: 24,
                  right: 16,
                  child: InkWell(
                    onTap: () => Navigator.of(context).pop(),
                    child: Container(
                      height: 38,
                      width: 38,
                      decoration: BoxDecoration(
                        color: const Color(0xFFF97316),
                        shape: BoxShape.circle,
                        boxShadow: const [
                          BoxShadow(color: Color(0x33000000), blurRadius: 8, offset: Offset(0, 4)),
                        ],
                      ),
                      child: const Icon(Icons.close, color: Colors.white),
                    ),
                  ),
                ),
                Positioned(
                  top: 26,
                  left: 16,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                    decoration: BoxDecoration(
                      color: Colors.black.withOpacity(0.45),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '${index + 1}/${photos.length}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  String _friendlyError(String raw) {
    final text = raw.toLowerCase();
    if (text.contains('timeout')) {
      return _tr(ru: 'Превышено время ожидания.', uz: 'Vaqt tugadi.');
    }
    if (text.contains('socket') || text.contains('network')) {
      return _tr(ru: 'Ошибка сети.', uz: 'Tarmoq xatosi.');
    }
    return _tr(ru: 'Произошла ошибка.', uz: 'Xatolik yuz berdi.');
  }

  String _priceModeLabel(String mode) {
    if (mode == 'hour') return _tr(ru: 'За час', uz: 'Soatlik');
    if (mode == 'month') return _tr(ru: 'За месяц', uz: 'Oylik');
    return _tr(ru: 'За день', uz: 'Kunlik');
  }

  String _fmtPrice(num v) {
    final s = v.toStringAsFixed(0);
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      final idx = s.length - i;
      buf.write(s[i]);
      if (idx > 1 && idx % 3 == 1) buf.write(' ');
    }
    return '${buf.toString()} so\'m';
  }

  String _fmtMinMaxPrice(num? minPrice, num? maxPrice, String mode) {
    if (minPrice == null) return _tr(ru: 'По договоренности', uz: 'Kelishiladi');
    if (maxPrice == null) {
      return '${_priceModeLabel(mode)}: ${_fmtPrice(minPrice)}';
    }
    return '${_tr(ru: "Мин цена", uz: "Min narx")}: ${_fmtPrice(minPrice)} | ${_tr(ru: "Макс цена", uz: "Max narx")}: ${_fmtPrice(maxPrice)}';
  }

  Future<void> _openMap() async {
    if (!mounted) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => ClientMapScreen(
          lang: _lang,
          branches: _filtered,
          onOpenBranch: (b) {
            Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => ClientBranchDetailsScreen(
                  lang: _lang,
                  branchId: b.id,
                  priceMode: _priceMode,
                ),
              ),
            );
          },
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final rangeMax = max(_priceMaxBound, _priceMinBound + 1);
    final range = RangeValues(
      _priceRange.start.clamp(_priceMinBound, rangeMax),
      _priceRange.end.clamp(_priceMinBound, rangeMax),
    );
    final totalPages = (_totalCount / _pageSize).ceil();
    final effectivePage = totalPages == 0 ? 1 : _page.clamp(1, totalPages);
    if (effectivePage != _page) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) setState(() => _page = effectivePage);
      });
    }
    final pageItems = _filtered;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        title: Text(_tr(ru: 'Каталог', uz: 'Katalog')),
        actions: [
          IconButton(
            tooltip: _tr(ru: 'Карта', uz: 'Xarita'),
            onPressed: _openMap,
            icon: Image.asset('assets/icons/map_show.png', width: 20, height: 20),
          ),
          IconButton(
            tooltip: _tr(ru: 'Язык', uz: 'Til'),
            onPressed: _openLangPicker,
            icon: Image.asset('assets/icons/language.png', width: 20, height: 20),
          ),
          IconButton(
            tooltip: _tr(ru: 'Профиль', uz: 'Profil'),
            onPressed: _openProfileMenu,
            icon: Image.asset('assets/icons/user.png', width: 20, height: 20),
          ),
        ],
      ),
      body: SafeArea(
        child: Stack(
          children: [
            Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _searchCtrl,
                          decoration: InputDecoration(
                            hintText: _tr(ru: 'Поиск...', uz: 'Qidirish...'),
                            prefixIcon: const Icon(Icons.search),
                            suffixIcon: _searchCtrl.text.trim().isEmpty
                                ? null
                                : IconButton(
                                    onPressed: () {
                                      _searchCtrl.clear();
                                      _applyClientFilters();
                                    },
                                    icon: const Icon(Icons.close),
                                  ),
                            filled: true,
                            fillColor: _card,
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: _border)),
                            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: _border)),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton(
                        onPressed: _filtersActive ? _resetFilters : _toggleFilters,
                        tooltip: _filtersActive
                            ? _tr(ru: 'Сбросить фильтры', uz: 'Filterni bekor qilish')
                            : (_filtersOpen ? _tr(ru: 'Скрыть фильтры', uz: 'Filterni yopish') : _tr(ru: 'Фильтры', uz: 'Filtrlar')),
                        icon: Image.asset(
                          _filtersActive ? 'assets/icons/clear-filter.png' : 'assets/icons/filter.png',
                          width: 20,
                          height: 20,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: RefreshIndicator(
                    onRefresh: () async {
                      await _loadAll();
                    },
                    child: _loading
                        ? ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            children: const [
                              SizedBox(height: 220),
                              Center(child: CircularProgressIndicator()),
                            ],
                          )
                        : _filtered.isEmpty
                            ? ListView(
                                physics: const AlwaysScrollableScrollPhysics(),
                                children: [
                                  const SizedBox(height: 120),
                                  Center(child: Text(_tr(ru: 'Ничего не найдено.', uz: 'Natija topilmadi.'))),
                                ],
                              )
                            : ListView.separated(
                                physics: const AlwaysScrollableScrollPhysics(),
                                padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                                itemCount: pageItems.length,
                                separatorBuilder: (_, __) => const SizedBox(height: 12),
                                itemBuilder: (_, i) => _buildBranchCard(pageItems[i]),
                              ),
                  ),
                ),
                if (totalPages >= 1 && _filtered.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 6, 16, 14),
                    child: _PaginationBar(
                      totalPages: totalPages,
                      currentPage: effectivePage,
                      onPageChanged: (p) {
                        setState(() => _page = p);
                        _loadBranches();
                      },
                    ),
                  ),
              ],
            ),
            if (_filtersOpening)
              Positioned.fill(
                child: Container(
                  color: Colors.black.withOpacity(0.15),
                  alignment: Alignment.center,
                  child: const CircularProgressIndicator(),
                ),
              ),
            if (_filtersOpen)
              Positioned.fill(
                child: GestureDetector(
                  onTap: _toggleFilters,
                  child: Container(color: Colors.black.withOpacity(0.25)),
                ),
              ),
            if (_filtersOpen)
              Center(
                child: Material(
                  color: _card,
                  elevation: 10,
                  borderRadius: BorderRadius.circular(20),
                  child: SizedBox(
                    width: 360,
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Row(
                            children: [
                              Text(_tr(ru: 'Фильтры', uz: 'Filtrlar'), style: const TextStyle(fontWeight: FontWeight.w700)),
                              const Spacer(),
                              IconButton(
                                onPressed: _toggleFilters,
                                icon: const Icon(Icons.close),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String?>(
                                  value: _regionSlug,
                                  hint: _dropdownPlaceholder(_tr(ru: 'Все области', uz: 'Barcha viloyatlar')),
                                  decoration: InputDecoration(
                                    hintText: _tr(ru: 'Все области', uz: 'Barcha viloyatlar'),
                                    hintStyle: const TextStyle(fontSize: 12, color: _textMuted),
                                    filled: true,
                                    fillColor: _card,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  ),
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
                                  dropdownColor: _card,
                                  items: _regionItems(),
                                  onChanged: (value) {
                                    setState(() {
                                      _regionSlug = value;
                                      if (_regionSlug == null) {
                                        _regionCtrl.clear();
                                      } else {
                                        final name = _regionNames().firstWhere(
                                          (n) => _regionSlugByName(n) == _regionSlug,
                                          orElse: () => '',
                                        );
                                        _regionCtrl.text = name;
                                      }
                                      _cityName = null;
                                      _cityCtrl.clear();
                                      _districtName = null;
                                      _districtCtrl.clear();
                                    });
                                    _applyClientFilters();
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: DropdownButtonFormField<String?>(
                                  value: _cityName,
                                  hint: _dropdownPlaceholder(_tr(ru: 'Все города', uz: 'Barcha shaharlar')),
                                  decoration: InputDecoration(
                                    hintText: _tr(ru: 'Все города', uz: 'Barcha shaharlar'),
                                    hintStyle: const TextStyle(fontSize: 12, color: _textMuted),
                                    filled: true,
                                    fillColor: _card,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                                  ),
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
                                  dropdownColor: _card,
                                  items: _cityItems(),
                                  onChanged: (value) {
                                    setState(() {
                                      _cityName = value;
                                      _cityCtrl.text = value ?? '';
                                      _districtName = null;
                                      _districtCtrl.clear();
                                    });
                                    _applyClientFilters();
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String?>(
                                  value: _districtName,
                                  hint: _dropdownPlaceholder(_tr(ru: 'Все районы', uz: 'Barcha tumanlar')),
                                  decoration: InputDecoration(
                                    hintText: _tr(ru: 'Все районы', uz: 'Barcha tumanlar'),
                                    hintStyle: const TextStyle(fontSize: 12, color: _textMuted),
                                    filled: true,
                                    fillColor: _card,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                                  ),
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
                                  dropdownColor: _card,
                                  items: _districtItems(),
                                  onChanged: (value) {
                                    setState(() {
                                      _districtName = value;
                                      _districtCtrl.text = value ?? '';
                                    });
                                    _applyClientFilters();
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: DropdownButtonFormField<String?>(
                                  value: _roomType,
                                  hint: _dropdownPlaceholder(_tr(ru: 'Все типы комнат', uz: 'Barcha xona turlari')),
                                  decoration: InputDecoration(
                                    hintText: _tr(ru: 'Все типы комнат', uz: 'Barcha xona turlari'),
                                    hintStyle: const TextStyle(fontSize: 12, color: _textMuted),
                                    filled: true,
                                    fillColor: _card,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  ),
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
                                  dropdownColor: _card,
                                  items: [
                                    DropdownMenuItem<String?>(
                                      value: null,
                                      child: _dropdownPlaceholder(_tr(ru: 'Все типы комнат', uz: 'Barcha xona turlari')),
                                    ),
                                    ..._roomTypeNames().map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
                                  ],
                                  onChanged: (value) {
                                    setState(() {
                                      _roomType = value;
                                      _roomTypeCtrl.text = value ?? '';
                                    });
                                    _applyClientFilters();
                                  },
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 10),
                          Row(
                            children: [
                              Expanded(
                                child: DropdownButtonFormField<String>(
                                  value: _priceMode,
                                  decoration: InputDecoration(
                                    hintText: _tr(ru: 'Режим цены', uz: 'Narx turi'),
                                    hintStyle: const TextStyle(fontSize: 12, color: _textMuted),
                                    filled: true,
                                    fillColor: _card,
                                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                                  ),
                                  style: const TextStyle(fontSize: 13, color: Color(0xFF0F172A)),
                                  dropdownColor: _card,
                                  items: [
                                    DropdownMenuItem(value: 'day', child: Text(_tr(ru: 'Сутки', uz: 'Kunlik'))),
                                    DropdownMenuItem(value: 'hour', child: Text(_tr(ru: 'Час', uz: 'Soatlik'))),
                                    DropdownMenuItem(value: 'month', child: Text(_tr(ru: 'Месяц', uz: 'Oylik'))),
                                  ],
                                  onChanged: (value) {
                                    if (value == null) return;
                                    setState(() {
                                      _priceMode = value;
                                      _page = 1;
                                      _priceRangeDirty = false;
                                    });
                                    _loadBranches();
                                  },
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(_tr(ru: 'Мин. рейтинг', uz: 'Reyting')),
                                    Slider(
                                      value: _minRating,
                                      min: 0,
                                      max: 5,
                                      divisions: 10,
                                      label: _minRating.toStringAsFixed(1),
                                      onChanged: (v) {
                                        setState(() => _minRating = v);
                                        _applyClientFilters();
                                      },
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_tr(ru: 'Дистанция', uz: 'Masofa')),
                              const SizedBox(height: 6),
                              Wrap(
                                spacing: 8,
                                children: [
                                  ChoiceChip(
                                    label: Text(_tr(ru: 'Все', uz: 'Hammasi')),
                                    selected: _distanceKm == null,
                                    onSelected: (_) {
                                      _setDistanceFilter(null);
                                    },
                                  ),
                                  for (final km in [1, 3, 5, 10, 20, 50])
                                    ChoiceChip(
                                      label: Text('$km km'),
                                      selected: _distanceKm == km.toDouble(),
                                      onSelected: (_) {
                                        _setDistanceFilter(km.toDouble());
                                      },
                                    ),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(_tr(ru: 'Диапазон цены', uz: 'Narx oralig\'i')),
                              RangeSlider(
                                min: _priceMinBound,
                                max: rangeMax,
                                values: range,
                                onChanged: (v) {
                                  setState(() {
                                    _priceRange = v;
                                    _priceRangeDirty = true;
                                  });
                                  _applyClientFilters();
                                },
                              ),
                              Row(
                                children: [
                                  Text('${range.start.toStringAsFixed(0)}'),
                                  const Spacer(),
                                  Text('${range.end.toStringAsFixed(0)}'),
                                ],
                              ),
                            ],
                          ),
                          const SizedBox(height: 6),
                          Row(
                            children: [
                              Expanded(
                                child: OutlinedButton(
                                  onPressed: _resetFilters,
                                  child: Text(_tr(ru: 'Сбросить', uz: 'Bekor qilish')),
                                ),
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: FilledButton(
                                  onPressed: _toggleFilters,
                                  child: Text(_tr(ru: 'Готово', uz: 'Tayyor')),
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildBranchCard(BranchSummary b) {
    final rating = b.rating != null ? b.rating!.toStringAsFixed(1) : '-';

    final minLine = b.minPrice != null
        ? '${_tr(ru: 'Мин цена', uz: 'Min narx')}: ${_fmtPrice(b.minPrice!)} so\'m'
        : null;
    final maxLine = b.maxPrice != null
        ? '${_tr(ru: 'Макс цена', uz: 'Max narx')}: ${_fmtPrice(b.maxPrice!)} so\'m'
        : null;
    final noPriceLine = (minLine == null && maxLine == null)
        ? '${_tr(ru: 'Нарх', uz: 'Narx')}: ${_tr(ru: 'По договоренности', uz: 'Kelishiladi')}'
        : null;
    final prepayLabel = b.prepayLabel(_lang);
    final hasPrepay = prepayLabel.trim().isNotEmpty;
    final photos = b.photos.isNotEmpty
        ? List<String>.from(b.photos)
        : (b.coverPhoto != null && b.coverPhoto!.trim().isNotEmpty
            ? <String>[b.coverPhoto!]
            : const <String>[]);
    final amenityTags = _parseAmenities(b.amenities, max: 6);
    String? distanceLabel;
    if (_distanceKm != null && _catalogUserPos != null && b.latitude != null && b.longitude != null) {
      final d = _distanceKmBetween(_catalogUserPos!, b.latitude!, b.longitude!);
      if (d != null) {
        distanceLabel = '${d.toStringAsFixed(1)} km';
      }
    }
    return Container(
      decoration: BoxDecoration(
        color: _card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _border),
        boxShadow: const [BoxShadow(color: Color(0x14000000), blurRadius: 12, offset: Offset(0, 6))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (photos.isNotEmpty)
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              child: SizedBox(
                height: 210,
                width: double.infinity,
                child: Stack(
                  fit: StackFit.expand,
                  children: [
                    GestureDetector(
                      onTap: () => _openBranchGallery(b),
                      child: Image.network(
                        photos.first,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => Container(
                          color: _surfaceSoft,
                          alignment: Alignment.center,
                          child: const Icon(Icons.image_not_supported_outlined),
                        ),
                      ),
                    ),
                    const IgnorePointer(
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          gradient: LinearGradient(
                            begin: Alignment.bottomCenter,
                            end: Alignment.topCenter,
                            colors: [Color(0x44000000), Colors.transparent],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            )
          else
            Container(
              height: 200,
              width: double.infinity,
              decoration: BoxDecoration(
                color: _surfaceSoft,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.hotel_outlined, size: 44, color: _textMuted),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Text(
                        b.name.isNotEmpty ? b.name : '#${b.id}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                      ),
                    ),
                    if (hasPrepay)
                      Container(
                        margin: const EdgeInsets.only(left: 8),
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFECFDF3),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFBBF7D0)),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            const Icon(Icons.verified, size: 14, color: Color(0xFF15803D)),
                            const SizedBox(width: 4),
                            Text(
                              prepayLabel,
                              style: const TextStyle(fontSize: 11, color: Color(0xFF166534), fontWeight: FontWeight.w600),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  () {
                    final parts = [
                      (b.regionName ?? '').trim(),
                      (b.cityName ?? '').trim(),
                      (b.districtName ?? '').trim(),
                    ].where((e) => e.isNotEmpty).toList();
                    if (parts.isNotEmpty) return parts.join(', ');
                    if ((b.address ?? '').trim().isNotEmpty) return b.address!.trim();
                    return _tr(ru: 'Адрес не указан', uz: 'Manzil ko\'rsatilmagan');
                  }(),
                  style: const TextStyle(color: _textMuted),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEFF6FF),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: _border),
                      ),
                      child: Text('⭐ $rating', style: const TextStyle(fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                if (minLine != null || maxLine != null || noPriceLine != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF1F5F9),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: _border),
                        ),
                        child: Text(
                          _tr(ru: 'Нарх', uz: 'Narx'),
                          style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: _textMuted),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (noPriceLine != null) Text(noPriceLine),
                            if (minLine != null) Text(minLine),
                            if (maxLine != null) Text(maxLine),
                          ],
                        ),
                      ),
                    ],
                  ),
                ],
                if (distanceLabel != null) ...[
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(Icons.place_outlined, size: 16, color: _textMuted),
                      const SizedBox(width: 6),
                      Text(
                        distanceLabel,
                        style: const TextStyle(fontWeight: FontWeight.w600, color: _textMuted),
                      ),
                    ],
                  ),
                ],
                const SizedBox(height: 10),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: () => Navigator.of(context).push(
                          MaterialPageRoute(
                            builder: (_) => ClientBranchDetailsScreen(
                              lang: _lang,
                              branchId: b.id,
                              priceMode: _priceMode,
                            ),
                          ),
                        ),
                        child: Text(_tr(ru: 'Подробнее', uz: 'Batafsil')),
                      ),
                    ),
                    const SizedBox(width: 8),
                    if (amenityTags.isNotEmpty)
                      SizedBox(
                        height: 40,
                        width: 44,
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            padding: EdgeInsets.zero,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          onPressed: () => _showAmenitiesModal(context, b),
                        child: Image.asset('assets/icons/letter-i.png', width: 20, height: 20),
                        ),
                      ),
                    if (amenityTags.isNotEmpty) const SizedBox(width: 8),
                    SizedBox(
                      height: 40,
                      width: 44,
                      child: OutlinedButton(
                        style: OutlinedButton.styleFrom(
                          padding: EdgeInsets.zero,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                        ),
                        onPressed: () => _openMaps(b),
                        child: Image.asset('assets/icons/destination.png', width: 20, height: 20),
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

  Future<void> _openMaps(BranchSummary b) async {
    if (b.latitude == null || b.longitude == null) return;
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=${b.latitude},${b.longitude}');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      _showSnack(_tr(ru: 'Не удалось открыть карту.', uz: 'Xaritani ochib bo\'lmadi.'), error: true);
    }
  }

  void _showAmenitiesModal(BuildContext context, BranchSummary b) {
    final tags = _parseAmenities(b.amenities, max: 40);
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        titlePadding: const EdgeInsets.fromLTRB(20, 16, 8, 0),
        contentPadding: const EdgeInsets.fromLTRB(20, 12, 20, 20),
        title: Row(
          children: [
            Expanded(
              child: Text(
                _tr(ru: 'Удобства', uz: 'Qulayliklar'),
                style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
              ),
            ),
            IconButton(onPressed: () => Navigator.of(context).pop(), icon: const Icon(Icons.close)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 4),
            if (tags.isEmpty)
              Text(
                _tr(ru: 'Информация отсутствует', uz: 'Maʼlumot mavjud emas'),
                style: const TextStyle(color: _textMuted),
              )
            else
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: tags
                    .map(
                      (t) => Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: _surfaceSoft,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: _border),
                        ),
                        child: Text(
                          t,
                          style: const TextStyle(fontSize: 12, color: _textMuted, fontWeight: FontWeight.w600),
                        ),
                      ),
                    )
                    .toList(),
              ),
          ],
        ),
      ),
    );
  }
}

class BranchSummary {
  BranchSummary({
    required this.id,
    required this.name,
    this.address,
    this.rating,
    this.ratingCount,
    this.minPrice,
    this.maxPrice,
    this.latitude,
    this.longitude,
    this.regionSlug,
    this.regionName,
    this.cityName,
    this.districtName,
    this.amenities,
    this.prepaymentEnabled = false,
    this.prepaymentMode,
    this.prepaymentValue,
    this.roomTypes = '',
    this.coverPhoto,
    this.photos = const [],
    this.status,
    this.statusCode,
    this.contactPhone,
    this.contactTelegram,
    this.roomPriceDaily,
    this.roomPriceHourly,
    this.roomPriceMonthly,
    this.minBedDailyPrice,
    this.maxBedDailyPrice,
    this.minBedHourlyPrice,
    this.maxBedHourlyPrice,
    this.minBedMonthlyPrice,
    this.maxBedMonthlyPrice,
  });

  final int id;
  final String name;
  final String? address;
  final double? rating;
  final int? ratingCount;
  final double? minPrice;
  final double? maxPrice;
  final double? latitude;
  final double? longitude;
  final String? regionSlug;
  final String? regionName;
  final String? cityName;
  final String? districtName;
  final String? amenities;
  final bool prepaymentEnabled;
  final String? prepaymentMode;
  final double? prepaymentValue;
  final String roomTypes;
  final String? coverPhoto;
  final List<String> photos;
  final String? status;
  final String? statusCode;
  final String? contactPhone;
  final String? contactTelegram;
  final double? roomPriceDaily;
  final double? roomPriceHourly;
  final double? roomPriceMonthly;
  final double? minBedDailyPrice;
  final double? maxBedDailyPrice;
  final double? minBedHourlyPrice;
  final double? maxBedHourlyPrice;
  final double? minBedMonthlyPrice;
  final double? maxBedMonthlyPrice;

  factory BranchSummary.fromJson(Map<String, dynamic> json) {
    double? _num(dynamic v) {
      if (v == null) return null;
      if (v is num) return v.toDouble();
      final s = v.toString().trim().replaceAll(' ', '').replaceAll(',', '.');
      return double.tryParse(s);
    }
    List<double>? _coords(dynamic v) {
      if (v is List && v.length >= 2) {
        final lon = _num(v[0]);
        final lat = _num(v[1]);
        if (lon == null || lat == null) return null;
        return [lon, lat];
      }
      if (v is Map) {
        final lat = _num(v['lat'] ?? v['latitude']);
        final lon = _num(v['lng'] ?? v['lon'] ?? v['longitude'] ?? v['long']);
        if (lon == null || lat == null) return null;
        return [lon, lat];
      }
      if (v is String) {
        final parts = v.split(',');
        if (parts.length >= 2) {
          final lat = _num(parts[0]);
          final lon = _num(parts[1]);
          if (lon == null || lat == null) return null;
          return [lon, lat];
        }
      }
      return null;
    }
    String? _photo(dynamic v) {
      if (v == null) return null;
      final raw = v.toString();
      if (raw.isEmpty) return null;
      if (raw.startsWith('//')) return 'https:$raw';
      if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
      if (raw.startsWith('/')) return '$_publicHost$raw';
      return '$_publicHost/$raw';
    }
    String? _pickFromList(dynamic list) {
      if (list is List && list.isNotEmpty) {
        final first = list.first;
        if (first is Map) {
          return _photo(first['url'] ?? first['photo'] ?? first['image']);
        }
        return _photo(first);
      }
      return null;
    }
    List<String> _photoList(dynamic list) {
      if (list is! List) return const [];
      final out = <String>[];
      for (final item in list) {
        String? url;
        if (item is Map) {
          url = _photo(item['url'] ?? item['photo'] ?? item['image']);
        } else {
          url = _photo(item);
        }
        if (url != null && url.isNotEmpty) {
          out.add(url);
        }
      }
      return out;
    }
    final coords = _coords(json['coordinates'] ?? json['coords'] ?? json['location']);
    double? lat = _num(json['latitude'] ?? json['lat']) ?? (coords != null ? coords[1] : null);
    double? lon = _num(json['longitude'] ?? json['lng'] ?? json['lon'] ?? json['long']) ?? (coords != null ? coords[0] : null);
    if (lat != null && lon != null && lat.abs() > 50 && lon.abs() < 50) {
      final tmp = lat;
      lat = lon;
      lon = tmp;
    }
    final cover = _photo(json['cover_photo'] ??
            json['coverPhoto'] ??
            json['cover_image'] ??
            json['coverImage'] ??
            json['cover_photo_url'] ??
            json['photo'] ??
            json['photo_url'] ??
            json['image']) ??
        _pickFromList(json['photos']) ??
        _pickFromList(json['images']);

    final list = [
      ..._photoList(json['photos']),
      ..._photoList(json['images']),
    ];
    if (cover != null && cover.isNotEmpty) {
      list.insert(0, cover);
    }
    final unique = <String>[];
    for (final url in list) {
      if (!unique.contains(url)) unique.add(url);
    }

    return BranchSummary(
      id: (json['id'] is num) ? (json['id'] as num).toInt() : int.tryParse(json['id'].toString()) ?? 0,
      name: (json['name'] ?? '').toString(),
      address: json['address']?.toString(),
      rating: _num(json['rating'] ?? json['avg_rating']),
      ratingCount: (json['rating_count'] is num) ? (json['rating_count'] as num).toInt() : null,
      minPrice: _num(json['min_price'] ?? json['minPrice']),
      maxPrice: _num(json['max_price'] ?? json['maxPrice']),
      latitude: lat,
      longitude: lon,
      regionSlug: json['region_slug']?.toString(),
      regionName: json['region_name']?.toString(),
      cityName: json['city_name']?.toString(),
      districtName: json['district_name']?.toString(),
      amenities: json['amenities']?.toString(),
      prepaymentEnabled: json['prepayment_enabled'] == true,
      prepaymentMode: json['prepayment_mode']?.toString(),
      prepaymentValue: _num(json['prepayment_value']),
      roomTypes: (json['room_types'] ?? json['roomTypes'] ?? '').toString(),
      coverPhoto: cover,
      photos: unique,
      status: json['status']?.toString(),
      statusCode: json['status_code']?.toString(),
      contactPhone: json['contact_phone']?.toString(),
      contactTelegram: json['contact_telegram']?.toString(),
      roomPriceDaily: _num(json['room_price_daily']),
      roomPriceHourly: _num(json['room_price_hourly']),
      roomPriceMonthly: _num(json['room_price_monthly']),
      minBedDailyPrice: _num(json['min_bed_daily_price']),
      maxBedDailyPrice: _num(json['max_bed_daily_price']),
      minBedHourlyPrice: _num(json['min_bed_hourly_price']),
      maxBedHourlyPrice: _num(json['max_bed_hourly_price']),
      minBedMonthlyPrice: _num(json['min_bed_monthly_price']),
      maxBedMonthlyPrice: _num(json['max_bed_monthly_price']),
    );
  }


  String priceLabel(String mode, String lang) {
    final minV = minPrice;
    final maxV = maxPrice;
    if (minV == null && maxV == null) return '';
    final suffix = mode == 'hour'
        ? (lang == 'ru' ? '/час' : '/soat')
        : mode == 'month'
            ? (lang == 'ru' ? '/мес' : '/oy')
            : (lang == 'ru' ? '/сутки' : '/kun');
    if (minV != null && maxV != null && minV != maxV) {
      return '${minV.toStringAsFixed(0)} - ${maxV.toStringAsFixed(0)} $suffix';
    }
    final v = (minV ?? maxV)!;
    return '${v.toStringAsFixed(0)} $suffix';
  }

  String prepayLabel(String lang) {
    if (!prepaymentEnabled) return '';
    final mode = (prepaymentMode ?? 'percent').toLowerCase();
    final v = prepaymentValue ?? 0;
    if (v <= 0) return '';
    if (mode == 'amount') {
      return lang == 'ru'
          ? 'Предоплата: ${v.toStringAsFixed(0)}'
          : 'Oldindan to‘lov: ${v.toStringAsFixed(0)}';
    }
    return lang == 'ru'
        ? 'Предоплата: ${v.toStringAsFixed(0)}%'
        : 'Oldindan to‘lov: ${v.toStringAsFixed(0)}%';
  }
}

class BookingPrepayConfig {
  BookingPrepayConfig({
    required this.enabled,
    this.amount,
    this.note,
  });

  final bool enabled;
  final double? amount;
  final String? note;

  factory BookingPrepayConfig.fromJson(Map<String, dynamic> json) {
    double? _num(dynamic v) => v == null ? null : (v is num ? v.toDouble() : double.tryParse(v.toString()));
    return BookingPrepayConfig(
      enabled: json['enabled'] == true || json['is_enabled'] == true || json['required'] == true,
      amount: _num(json['amount'] ?? json['value']),
      note: json['note']?.toString(),
    );
  }

  String label(String lang) {
    if (!enabled) return '';
    if (amount != null) {
      if (amount! > 0) {
        return lang == 'ru'
            ? 'Предоплата: ${amount!.toStringAsFixed(0)}'
            : 'Oldindan to\'lov: ${amount!.toStringAsFixed(0)}';
      }
      return '';
    }
    if (note != null && note!.trim().isNotEmpty) {
      final hasNonZeroDigit = RegExp(r'[1-9]').hasMatch(note!);
      if (!hasNonZeroDigit) return '';
      return note!;
    }
    return '';
  }
}

class _PaginationBar extends StatelessWidget {
  const _PaginationBar({
    required this.totalPages,
    required this.currentPage,
    required this.onPageChanged,
  });

  final int totalPages;
  final int currentPage;
  final ValueChanged<int> onPageChanged;

  @override
  Widget build(BuildContext context) {
    if (totalPages <= 0) return const SizedBox.shrink();

    if (totalPages == 1) {
      return Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _pageChip(1, selected: true, onTap: () {}),
        ],
      );
    }

    final pages = <int>{};
    pages.add(1);
    pages.add(totalPages);
    for (int i = currentPage - 2; i <= currentPage + 2; i++) {
      if (i >= 1 && i <= totalPages) pages.add(i);
    }
    final ordered = pages.toList()..sort();

    Widget buildDot() => const SizedBox(
          width: 18,
          child: Text('• • •', textAlign: TextAlign.center, style: TextStyle(color: _textMuted)),
        );

    List<Widget> items = [];
    items.add(_pageIcon(
      Icons.keyboard_arrow_left,
      enabled: currentPage > 1,
      onTap: () => onPageChanged(currentPage - 1),
    ));

    int? prev;
    for (final p in ordered) {
      if (prev != null && p - prev! > 1) {
        items.add(buildDot());
      }
      items.add(_pageChip(p, selected: p == currentPage, onTap: () => onPageChanged(p)));
      prev = p;
    }

    items.add(_pageIcon(
      Icons.keyboard_arrow_right,
      enabled: currentPage < totalPages,
      onTap: () => onPageChanged(currentPage + 1),
    ));

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: items
          .expand((w) => [w, const SizedBox(width: 8)])
          .toList()
        ..removeLast(),
    );
  }

  Widget _pageChip(int page, {required bool selected, required VoidCallback onTap}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        height: 32,
        width: 32,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: selected ? _brandBlue : _card,
          border: Border.all(color: selected ? _brandBlue : _border),
        ),
        child: Text(
          '$page',
          style: TextStyle(
            fontWeight: FontWeight.w700,
            color: selected ? Colors.white : _textMuted,
          ),
        ),
      ),
    );
  }

  Widget _pageIcon(IconData icon, {required bool enabled, required VoidCallback onTap}) {
    return InkWell(
      onTap: enabled ? onTap : null,
      borderRadius: BorderRadius.circular(18),
      child: Container(
        height: 32,
        width: 32,
        alignment: Alignment.center,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: enabled ? _card : const Color(0xFFE2E8F0),
          border: Border.all(color: _border),
        ),
        child: Icon(icon, size: 18, color: enabled ? _textMuted : const Color(0xFF94A3B8)),
      ),
    );
  }
}

class UserHistoryItem {
  UserHistoryItem({
    required this.branchId,
    required this.branchName,
    required this.message,
    required this.itemType,
    required this.createdAt,
  });

  final int branchId;
  final String branchName;
  final String message;
  final String itemType;
  final DateTime? createdAt;

  factory UserHistoryItem.fromJson(Map<String, dynamic> json) {
    DateTime? _date(dynamic v) {
      if (v == null) return null;
      try {
        return DateTime.parse(v.toString());
      } catch (_) {
        return null;
      }
    }

    return UserHistoryItem(
      branchId: (json['branch_id'] is num) ? (json['branch_id'] as num).toInt() : int.tryParse(json['branch_id'].toString()) ?? 0,
      branchName: (json['branch_name'] ?? '').toString(),
      message: (json['message'] ?? '').toString(),
      itemType: (json['item_type'] ?? '').toString(),
      createdAt: _date(json['created_at']),
    );
  }

  String itemTypeLabel(String lang) {
    final type = itemType.toLowerCase();
    if (type == 'booking') return lang == 'ru' ? 'Бронь' : 'Bron';
    if (type == 'feedback') return lang == 'ru' ? 'Отзыв' : 'Fikr';
    return lang == 'ru' ? 'История' : 'Tarix';
  }
}

class ClientMapScreen extends StatefulWidget {
  const ClientMapScreen({
    super.key,
    required this.lang,
    required this.branches,
    required this.onOpenBranch,
  });

  final String lang;
  final List<BranchSummary> branches;
  final ValueChanged<BranchSummary> onOpenBranch;

  @override
  State<ClientMapScreen> createState() => _ClientMapScreenState();
}

class _ClientMapScreenState extends State<ClientMapScreen> with WidgetsBindingObserver {
  mb.MapboxMap? _map;
  mb.PointAnnotationManager? _pointManager;
  mb.CircleAnnotationManager? _circleManager;
  final Map<String, BranchSummary> _branchByAnnotation = {};
  LatLng? _userPos;
  String? _error;
  double? _distanceKm;
  Timer? _pulseTimer;
  int _pulseStep = 0;
  bool _styleReady = false;
  Uint8List? _iconFreeBytes;
  Uint8List? _iconBusyBytes;
  Uint8List? _iconPartialBytes;
  Uint8List? _userBytes;
  double _iconScale = 0.26;
  double _textSize = 10;
  double? _lastZoom;
  double? _currentZoom;
  double? _lastRadiusZoom;
  StreamSubscription<geo.Position>? _posSub;
  bool _pickLocation = false;
  bool _needsLocationRetry = false;

  String _tr(String ru, String uz) => widget.lang == 'ru' ? ru : uz;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ensureLocation();
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _posSub?.cancel();
    _pulseTimer?.cancel();
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed && (_needsLocationRetry || _userPos == null)) {
      _needsLocationRetry = false;
      _ensureLocation();
    }
  }

  Future<void> _ensureLocation() async {
    try {
      if (mounted) setState(() => _error = null);
      final serviceEnabled = await geo.Geolocator.isLocationServiceEnabled();
      if (!serviceEnabled) {
        await geo.Geolocator.openLocationSettings();
        _needsLocationRetry = true;
        setState(() => _error = _tr('Включите GPS.', 'GPS yoqing.'));
        return;
      }
      var permission = await geo.Geolocator.checkPermission();
      if (permission == geo.LocationPermission.denied) {
        permission = await geo.Geolocator.requestPermission();
      }
      if (permission == geo.LocationPermission.denied || permission == geo.LocationPermission.deniedForever) {
        if (permission == geo.LocationPermission.deniedForever) {
          await geo.Geolocator.openAppSettings();
        }
        _needsLocationRetry = true;
        setState(() => _error = _tr('Нет доступа к GPS.', 'GPS ruxsati berilmadi.'));
        return;
      }
      // Start listening to location updates to keep user marker visible.
      _posSub?.cancel();
      _posSub = geo.Geolocator.getPositionStream(
        locationSettings: const geo.LocationSettings(
          accuracy: geo.LocationAccuracy.high,
          distanceFilter: 10,
        ),
      ).listen((pos) {
        if (!mounted) return;
        setState(() {
          _userPos = LatLng(pos.latitude, pos.longitude);
          _error = null;
        });
        _refreshMarkers();
      });
      geo.Position? pos;
      try {
        pos = await geo.Geolocator.getCurrentPosition(
          desiredAccuracy: geo.LocationAccuracy.high,
          timeLimit: const Duration(seconds: 12),
        );
      } catch (_) {
        // Fallback to last known or lower accuracy if GPS is slow
        pos = await geo.Geolocator.getLastKnownPosition();
        pos ??= await geo.Geolocator.getCurrentPosition(
          desiredAccuracy: geo.LocationAccuracy.low,
          timeLimit: const Duration(seconds: 10),
        );
      }
      if (!mounted) return;
      if (pos != null) {
        setState(() {
          _userPos = LatLng(pos!.latitude, pos!.longitude);
          _error = null;
        });
        await _centerOnUser();
      } else {
        setState(() => _error = _tr('Не удалось получить GPS.', 'GPS olinmadi.'));
        return;
      }
      await _refreshMarkers();
    } catch (_) {
      if (!mounted) return;
      setState(() => _error = _tr('Не удалось получить GPS.', 'GPS olinmadi.'));
    }
  }

  Future<Uint8List> _loadAssetBytes(String path) async {
    final data = await rootBundle.load(path);
    return data.buffer.asUint8List();
  }

  Future<mb.MbxImage> _loadMbxImage(String path) async {
    final bytes = await _loadAssetBytes(path);
    final codec = await ui.instantiateImageCodec(bytes);
    final frame = await codec.getNextFrame();
    final image = frame.image;
    final rgba = await image.toByteData(format: ui.ImageByteFormat.rawRgba);
    image.dispose();
    return mb.MbxImage(
      width: image.width,
      height: image.height,
      data: rgba!.buffer.asUint8List(),
    );
  }

  String _iconForBranch(BranchSummary b) {
    final code = (b.statusCode ?? b.status ?? '').toLowerCase();
    if (code.contains('busy')) return 'hotel_busy';
    if (code.contains('partial')) return 'hotel_partial_busy';
    return 'hotel_free';
  }

  Uint8List? _iconBytesForBranch(BranchSummary b) {
    final code = (b.statusCode ?? b.status ?? '').toLowerCase();
    if (code.contains('busy')) return _iconBusyBytes;
    if (code.contains('partial')) return _iconPartialBytes;
    return _iconFreeBytes;
  }

  Future<void> _setupMap(mb.MapboxMap map) async {
    _map = map;
    _pointManager = await map.annotations.createPointAnnotationManager();
    _circleManager = await map.annotations.createCircleAnnotationManager();
    _pointManager?.addOnPointAnnotationClickListener(_MapPointClickListener((annotation) {
      final b = _branchByAnnotation[annotation.id];
      if (b != null) widget.onOpenBranch(b);
    }));
    await _refreshMarkers();
  }

  Future<void> _onStyleLoaded(mb.StyleLoadedEventData data) async {
    if (_map == null) return;
    _styleReady = true;
    _iconFreeBytes ??= await _loadAssetBytes('assets/icons/hotel_free.png');
    _iconBusyBytes ??= await _loadAssetBytes('assets/icons/hotel_busy.png');
    _iconPartialBytes ??= await _loadAssetBytes('assets/icons/hotel_partial_busy.png');
    _userBytes ??= await _loadAssetBytes('assets/icons/navigation_human.png');
    await _map!.style.addStyleImage('hotel_free', 1.0, await _loadMbxImage('assets/icons/hotel_free.png'), false, const [], const [], null);
    await _map!.style.addStyleImage('hotel_busy', 1.0, await _loadMbxImage('assets/icons/hotel_busy.png'), false, const [], const [], null);
    await _map!.style.addStyleImage('hotel_partial_busy', 1.0, await _loadMbxImage('assets/icons/hotel_partial_busy.png'), false, const [], const [], null);
    await _map!.style.addStyleImage('user_loc', 1.0, await _loadMbxImage('assets/icons/navigation_human.png'), false, const [], const [], null);
    await _refreshMarkers();
  }

  void _onCameraChanged(mb.CameraChangedEventData data) {
    final zoom = data.cameraState.zoom;
    _currentZoom = zoom;
    if (_lastZoom != null && (zoom - _lastZoom!).abs() < 0.3) return;
    _lastZoom = zoom;
    final scale = (zoom / 13) * 0.26;
    final text = (zoom / 13) * 10;
    final nextScale = scale.clamp(0.16, 0.45);
    final nextText = text.clamp(8, 12).toDouble();
    if ((nextScale - _iconScale).abs() > 0.01 || (nextText - _textSize).abs() > 0.2) {
      _iconScale = nextScale;
      _textSize = nextText;
      _refreshMarkers();
    }
    if (_distanceKm != null) {
      if (_lastRadiusZoom == null || (zoom - _lastRadiusZoom!).abs() >= 0.4) {
        _lastRadiusZoom = zoom;
        _drawRadius();
      }
    }
  }

  Future<void> _refreshMarkers() async {
    if (_map == null || _pointManager == null) return;
    _iconFreeBytes ??= await _loadAssetBytes('assets/icons/hotel_free.png');
    _iconBusyBytes ??= await _loadAssetBytes('assets/icons/hotel_busy.png');
    _iconPartialBytes ??= await _loadAssetBytes('assets/icons/hotel_partial_busy.png');
    _userBytes ??= await _loadAssetBytes('assets/icons/navigation_human.png');
    _branchByAnnotation.clear();
    await _pointManager!.deleteAll();
    await _circleManager?.deleteAll();

    final list = _filteredBranches();
    for (final b in list) {
      if (b.latitude == null || b.longitude == null) continue;
      final annotation = await _pointManager!.create(
        mb.PointAnnotationOptions(
          geometry: mb.Point(coordinates: mb.Position(b.longitude!, b.latitude!)),
          image: _iconBytesForBranch(b),
          iconSize: _iconScale,
          iconAnchor: mb.IconAnchor.BOTTOM,
          textField: b.name,
          textSize: _textSize,
          textAnchor: mb.TextAnchor.TOP,
          textOffset: const [0, 1.2],
          textColor: const Color(0xFF111827).value,
          textHaloColor: const Color(0xFFFFFFFF).value,
          textHaloWidth: 1.2,
        ),
      );
      _branchByAnnotation[annotation.id] = b;
    }

    if (_userPos != null) {
      await _pointManager!.create(
        mb.PointAnnotationOptions(
          geometry: mb.Point(coordinates: mb.Position(_userPos!.longitude, _userPos!.latitude)),
          image: _userBytes,
          iconSize: _iconScale * 0.9,
          iconAnchor: mb.IconAnchor.BOTTOM,
        ),
      );
      if (_distanceKm != null) {
        await _drawRadius();
      } else {
        _pulseTimer?.cancel();
        await _circleManager?.deleteAll();
      }
    }
  }

  List<BranchSummary> _filteredBranches() {
    if (_distanceKm == null || _userPos == null) return widget.branches;
    final distance = Distance();
    return widget.branches.where((b) {
      if (b.latitude == null || b.longitude == null) return false;
      final d = distance.as(
        LengthUnit.Kilometer,
        _userPos!,
        LatLng(b.latitude!, b.longitude!),
      );
      return d <= _distanceKm!;
    }).toList();
  }

  Future<void> _drawRadius() async {
    if (_circleManager == null || _userPos == null) return;
    if (_distanceKm == null) {
      await _circleManager?.deleteAll();
      return;
    }
    _pulseTimer?.cancel();
    await _circleManager!.deleteAll();
    final zoom = (_currentZoom ?? await _map!.getCameraState().then((v) => v.zoom)) ?? 12.0;
    final lat = _userPos!.latitude;
    final metersPerPixel = 156543.03392 * cos(lat * pi / 180) / pow(2, zoom);
    final radiusMeters = _distanceKm! * 1000;
    final radiusPixels = radiusMeters / metersPerPixel;
    await _circleManager!.create(
      mb.CircleAnnotationOptions(
        geometry: mb.Point(coordinates: mb.Position(_userPos!.longitude, _userPos!.latitude)),
        circleRadius: radiusPixels,
        circleOpacity: 0.12,
        circleColor: const Color(0xFFF59E0B).value,
        circleStrokeColor: const Color(0xFFF59E0B).value,
        circleStrokeWidth: 2.5,
      ),
    );
  }

  void _setDistance(double? km) {
    setState(() => _distanceKm = km);
    if (_userPos == null && _map != null) {
      _map!.getCameraState().then((state) {
        if (!mounted || _userPos != null) return;
        final center = state.center.coordinates;
        setState(() => _userPos = LatLng(center.lat.toDouble(), center.lng.toDouble()));
        _centerOnUser();
        _refreshMarkers();
        _drawRadius();
      });
    } else {
      _centerOnUser();
      _refreshMarkers();
      _drawRadius();
    }
  }

  void _togglePickLocation() async {
    if (_map == null) return;
    if (!_pickLocation) {
      setState(() => _pickLocation = true);
      return;
    }
    // Confirm selection at map center
    final state = await _map!.getCameraState();
    final center = state.center.coordinates;
    if (!mounted) return;
    setState(() {
      _userPos = LatLng(center.lat.toDouble(), center.lng.toDouble());
      _error = null;
      _pickLocation = false;
    });
    await _centerOnUser();
    _refreshMarkers();
  }

  void _onMapTap(mb.MapContentGestureContext context) {
    if (!_pickLocation) return;
    final coords = context.point.coordinates;
    if (!mounted) return;
    setState(() {
      _userPos = LatLng(coords.lat.toDouble(), coords.lng.toDouble());
      _error = null;
      _pickLocation = false;
    });
    _centerOnUser();
    _refreshMarkers();
  }

  Future<void> _centerOnUser() async {
    if (_map == null || _userPos == null) return;
    await _map!.setCamera(
      mb.CameraOptions(
        center: mb.Point(coordinates: mb.Position(_userPos!.longitude, _userPos!.latitude)),
        zoom: 13.2,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final token = _mapboxToken();
    return Scaffold(
      appBar: AppBar(
        title: Text(_tr('Карта', 'Xarita')),
      ),
      body: Column(
        children: [
          Expanded(
            child: Builder(
              builder: (_) {
                if (token.isEmpty) {
                  return Container(
                    padding: const EdgeInsets.all(16),
                    alignment: Alignment.center,
                    child: Text(_tr('MAPBOX_TOKEN не задан.', 'MAPBOX_TOKEN yo‘q.')),
                  );
                }
                mb.MapboxOptions.setAccessToken(token);
                return Stack(
                  children: [
                    mb.MapWidget(
                      key: const ValueKey('client_map'),
                      styleUri: mb.MapboxStyles.STANDARD,
                      cameraOptions: _userPos == null
                          ? mb.CameraOptions(center: mb.Point(coordinates: mb.Position(69.2797, 41.3111)), zoom: 11.5)
                          : mb.CameraOptions(
                              center: mb.Point(coordinates: mb.Position(_userPos!.longitude, _userPos!.latitude)),
                              zoom: 13.2,
                            ),
                      onMapCreated: _setupMap,
                      onStyleLoadedListener: _onStyleLoaded,
                      onCameraChangeListener: _onCameraChanged,
                      onTapListener: _onMapTap,
                    ),
                    if (_pickLocation)
                      Center(
                        child: Image.asset(
                          'assets/icons/arrows.png',
                          width: 32,
                          height: 32,
                        ),
                      ),
                    Positioned(
                      right: 12,
                      top: 12,
                      child: FloatingActionButton(
                        heroTag: 'gps_btn',
                        mini: true,
                        backgroundColor: Colors.white,
                        elevation: 0,
                        highlightElevation: 0,
                        focusElevation: 0,
                        hoverElevation: 0,
                        onPressed: _togglePickLocation,
                        child: _pickLocation
                            ? Image.asset('assets/icons/arrows.png', width: 18, height: 18)
                            : const Icon(Icons.my_location, color: Color(0xFF1D4ED8)),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
          if (_error != null && _userPos == null)
            Padding(
              padding: const EdgeInsets.all(8),
              child: Text(_error!, style: const TextStyle(color: Color(0xFFDC2626))),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
            child: Row(
              children: [
                Text(_tr('Дистанция', 'Masofa')),
                const SizedBox(width: 10),
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        ChoiceChip(
                          label: Text(_tr('Все', 'Hammasi')),
                          selected: _distanceKm == null,
                          onSelected: (_) => _setDistance(null),
                        ),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('3 km'), selected: _distanceKm == 3, onSelected: (_) => _setDistance(3)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('5 km'), selected: _distanceKm == 5, onSelected: (_) => _setDistance(5)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('10 km'), selected: _distanceKm == 10, onSelected: (_) => _setDistance(10)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('20 km'), selected: _distanceKm == 20, onSelected: (_) => _setDistance(20)),
                        const SizedBox(width: 8),
                        ChoiceChip(label: const Text('50 km'), selected: _distanceKm == 50, onSelected: (_) => _setDistance(50)),
                      ],
                    ),
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

class _MapPointClickListener implements mb.OnPointAnnotationClickListener {
  _MapPointClickListener(this.onClick);

  final void Function(mb.PointAnnotation) onClick;

  @override
  void onPointAnnotationClick(mb.PointAnnotation annotation) {
    onClick(annotation);
  }
}

class ClientBranchDetailsScreen extends StatefulWidget {
  const ClientBranchDetailsScreen({
    super.key,
    required this.lang,
    required this.branchId,
    required this.priceMode,
  });

  final String lang;
  final int branchId;
  final String priceMode;

  @override
  State<ClientBranchDetailsScreen> createState() => _ClientBranchDetailsScreenState();
}

class _ClientBranchDetailsScreenState extends State<ClientBranchDetailsScreen> {
  BranchSummary? _branch;
  List<RoomSummary> _rooms = [];
  bool _loading = true;
  final Map<int, PageController> _roomPageCtrls = {};
  final Map<int, int> _roomImageIndex = {};

  String _tr(String ru, String uz) => widget.lang == 'ru' ? ru : uz;

  String _priceModeLabel(String mode) {
    if (mode == 'hour') return _tr('За час', 'Soatlik');
    if (mode == 'month') return _tr('За месяц', 'Oylik');
    return _tr('За день', 'Kunlik');
  }

  String _fmtPrice(num v) {
    final s = v.toStringAsFixed(0);
    final buf = StringBuffer();
    for (int i = 0; i < s.length; i++) {
      final idx = s.length - i;
      buf.write(s[i]);
      if (idx > 1 && idx % 3 == 1) buf.write(' ');
    }
    return '${buf.toString()} so\'m';
  }

  String _fmtMinMaxPrice(num? minPrice, num? maxPrice, String mode) {
    if (minPrice == null) return _tr('По договоренности', 'Kelishiladi');
    if (maxPrice == null) {
      return '${_priceModeLabel(mode)}: ${_fmtPrice(minPrice)}';
    }
    return '${_tr("Min narx", "Min narx")}: ${_fmtPrice(minPrice)} | ${_tr("Max narx", "Max narx")}: ${_fmtPrice(maxPrice)}';
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  Widget _infoTile(String label, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: _border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontSize: 11.5, color: _textMuted)),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    for (final c in _roomPageCtrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final uri = Uri.parse('$_publicApiBase/branches/${widget.branchId}/details')
          .replace(queryParameters: {'price_mode': widget.priceMode});
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (data is Map<String, dynamic>) {
          final branchRaw = data['branch'];
          final roomsRaw = data['rooms'];
          if (branchRaw is Map<String, dynamic>) {
            _branch = BranchSummary.fromJson(branchRaw);
          } else if (branchRaw is Map) {
            _branch = BranchSummary.fromJson(branchRaw.cast<String, dynamic>());
          }
          if (roomsRaw is List) {
            _rooms = roomsRaw
                .whereType<Map>()
                .map((e) => RoomSummary.fromJson(e.cast<String, dynamic>()))
                .toList();
          }
        }
      }
    } catch (_) {} finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_tr('Детали', 'Batafsil'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _branch == null
              ? Center(child: Text(_tr('Не удалось загрузить.', 'Yuklab bo\'lmadi.')))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    if (_branch!.coverPhoto != null && _branch!.coverPhoto!.trim().isNotEmpty) ...[
                      ClipRRect(
                        borderRadius: BorderRadius.circular(16),
                        child: Image.network(
                          _branch!.coverPhoto!,
                          height: 190,
                          width: double.infinity,
                          fit: BoxFit.cover,
                          errorBuilder: (_, __, ___) => Container(
                            height: 190,
                            color: _surfaceSoft,
                            alignment: Alignment.center,
                            child: const Icon(Icons.image_not_supported_outlined),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                    ],
                    Text(_branch!.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    Text(_branch!.address ?? '-', style: const TextStyle(color: _textMuted)),
                    ...(() {
                      final tags = _parseAmenities(_branch!.amenities, max: 10);
                      if (tags.isEmpty) return const <Widget>[];
                      return <Widget>[
                        const SizedBox(height: 8),
                        Wrap(
                          spacing: 8,
                          runSpacing: 8,
                          children: tags
                              .map(
                                (t) => Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                  decoration: BoxDecoration(
                                    color: _surfaceSoft,
                                    borderRadius: BorderRadius.circular(14),
                                    border: Border.all(color: _border),
                                  ),
                                  child: Text(
                                    t,
                                    style: const TextStyle(fontSize: 12, color: _textMuted, fontWeight: FontWeight.w600),
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                      ];
                    })(),
                    const SizedBox(height: 6),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            '⭐ ${_branch!.rating?.toStringAsFixed(1) ?? '-'} (${_branch!.ratingCount ?? 0})',
                            style: const TextStyle(color: _textMuted),
                          ),
                        ),
                        if (_branch!.contactPhone != null && _branch!.contactPhone!.isNotEmpty)
                          Padding(
                            padding: const EdgeInsets.only(left: 8),
                            child: InkWell(
                              onTap: () => _launchPhone(_branch!.contactPhone!),
                              borderRadius: BorderRadius.circular(18),
                              child: Ink(
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
                                decoration: BoxDecoration(
                                  gradient: const LinearGradient(
                                    colors: [Color(0xFF34D399), Color(0xFF16A34A)],
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                  ),
                                  borderRadius: BorderRadius.circular(18),
                                  boxShadow: const [
                                    BoxShadow(
                                      color: Color(0x3322C55E),
                                      blurRadius: 8,
                                      offset: Offset(0, 4),
                                    ),
                                  ],
                                ),
                                child: Text(
                                  _tr('Qo\'ng\'iroq', 'Qo\'ng\'iroq'),
                                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600, color: Colors.white),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                    ...(() {
                      final label = _branch!.prepayLabel(widget.lang);
                      if (label.trim().isEmpty) return const <Widget>[];
                      return <Widget>[
                        const SizedBox(height: 10),
                        Text(label, style: const TextStyle(color: _textMuted)),
                      ];
                    })(),
                    const SizedBox(height: 16),
                    ..._buildRoomCards(),
                    const SizedBox(height: 10),
                    FilledButton(
                      onPressed: () => _openMaps(_branch!),
                      child: Text(_tr('Открыть карту', 'Xaritani ochish')),
                    ),
                  ],
                ),
    );
  }

  Widget _infoChip(String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFFF1F5F9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _border),
      ),
      child: Text(text, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }

  Future<void> _openMaps(BranchSummary b) async {
    if (b.latitude == null || b.longitude == null) return;
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=${b.latitude},${b.longitude}');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _launchPhone(String phone) async {
    final uri = Uri.parse('tel:${phone.replaceAll(' ', '')}');
    await launchUrl(uri);
  }

  Future<void> _openTelegram(String raw) async {
    final clean = raw.trim().replaceAll('@', '');
    if (clean.isEmpty) return;
    final uri = Uri.parse('https://t.me/$clean');
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  Future<void> _openImageZoom(String url) async {
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (_) => Dialog(
        insetPadding: const EdgeInsets.all(12),
        backgroundColor: Colors.black,
        child: Stack(
          children: [
            InteractiveViewer(
              minScale: 1,
              maxScale: 4,
              child: Image.network(
                url,
                fit: BoxFit.contain,
                errorBuilder: (_, __, ___) => const Center(
                  child: Icon(Icons.image_not_supported_outlined, color: Colors.white),
                ),
              ),
            ),
            Positioned(
              top: 6,
              right: 6,
              child: IconButton(
                onPressed: () => Navigator.of(context).pop(),
                icon: const Icon(Icons.close, color: Color(0xFFF59E0B)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  List<Widget> _buildRoomCards() {
    final visible = _rooms.where((r) => (r.availableBeds ?? 0) > 0).toList();
    if (visible.isEmpty) {
      return [Text(_tr('Ma\'lumot topilmadi', 'Ma\'lumot topilmadi'), style: const TextStyle(color: _textMuted))];
    }
    return visible.map((r) {
      final roomDaily = _fmtMinMaxPrice(r.roomPriceDaily, r.roomPriceDaily, 'day');
      final roomHourly = _fmtMinMaxPrice(r.roomPriceHourly, r.roomPriceHourly, 'hour');
      final roomMonthly = _fmtMinMaxPrice(r.roomPriceMonthly, r.roomPriceMonthly, 'month');
      final bedDaily = _fmtMinMaxPrice(r.minBedDailyPrice, r.maxBedDailyPrice, 'day');
      final bedHourly = _fmtMinMaxPrice(r.minBedHourlyPrice, r.maxBedHourlyPrice, 'hour');
      final bedMonthly = _fmtMinMaxPrice(r.minBedMonthlyPrice, r.maxBedMonthlyPrice, 'month');
      final label = r.roomName ?? r.roomNumber ?? '-';
      final roomId = r.id ?? r.roomNumber.hashCode;
      final images = r.images.isNotEmpty
          ? r.images
          : (r.coverImage != null && r.coverImage!.isNotEmpty ? [r.coverImage!] : <String>[]);
      final controller = _roomPageCtrls.putIfAbsent(roomId, () => PageController());
      final currentIdx = _roomImageIndex[roomId] ?? 0;
      final status = _occupancyLabel(r.occupancyStatus);
      return Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: _card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: _border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Stack(
                children: [
                  SizedBox(
                    height: 190,
                    width: double.infinity,
                    child: images.isEmpty
                        ? Container(
                            color: _surfaceSoft,
                            alignment: Alignment.center,
                            child: const Icon(Icons.image_not_supported_outlined),
                          )
                        : PageView.builder(
                            controller: controller,
                            itemCount: images.length,
                            onPageChanged: (idx) {
                              setState(() => _roomImageIndex[roomId] = idx);
                            },
                            itemBuilder: (_, i) => GestureDetector(
                              onTap: () => _openImageZoom(images[i]),
                              child: Image.network(
                                images[i],
                                fit: BoxFit.cover,
                                errorBuilder: (_, __, ___) => Container(
                                  color: _surfaceSoft,
                                  alignment: Alignment.center,
                                  child: const Icon(Icons.image_not_supported_outlined),
                                ),
                              ),
                            ),
                          ),
                  ),
                  Positioned(
                    top: 10,
                    right: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.9),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(color: _border),
                      ),
                      child: Text(status, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                    ),
                  ),
                ],
              ),
            ),
            if (images.length > 1) ...[
              const SizedBox(height: 8),
              SizedBox(
                height: 54,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: images.length,
                  separatorBuilder: (_, __) => const SizedBox(width: 8),
                  itemBuilder: (_, i) {
                    final active = i == currentIdx;
                    return GestureDetector(
                      onTap: () {
                        controller.animateToPage(
                          i,
                          duration: const Duration(milliseconds: 250),
                          curve: Curves.easeOut,
                        );
                        setState(() => _roomImageIndex[roomId] = i);
                      },
                      child: Container(
                        width: 68,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: active ? const Color(0xFF2563EB) : _border, width: active ? 2 : 1),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.network(
                            images[i],
                            fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(
                              color: _surfaceSoft,
                              alignment: Alignment.center,
                              child: const Icon(Icons.image_not_supported_outlined, size: 18),
                            ),
                          ),
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
            const SizedBox(height: 10),
            Text(
              label,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: _infoTile(_tr('Xona turi', 'Xona turi'), _roomTypeLabel(r.roomType))),
                const SizedBox(width: 8),
                Expanded(child: _infoTile(_tr('Bron rejimi', 'Bron rejimi'), _bookingModeLabel(r.bookingMode))),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(child: _infoTile(_tr('Kravatlar', 'Kravatlar'), _bedBreakdown(r))),
                const SizedBox(width: 8),
                Expanded(child: _infoTile(_tr('Bo\'sh o\'rin', 'Bo\'sh o\'rin'), (r.availableBeds ?? 0).toString())),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: const Color(0xFFF8FAFC),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _border),
              ),
              child: _RoomPriceTabs(
                roomDaily: roomDaily,
                roomHourly: roomHourly,
                roomMonthly: roomMonthly,
                bedDaily: bedDaily,
                bedHourly: bedHourly,
                bedMonthly: bedMonthly,
                lang: widget.lang,
              ),
            ),
            const SizedBox(height: 10),
            SizedBox(
              width: double.infinity,
              child: FilledButton(
                onPressed: () => _openBooking(r),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Image.asset('assets/icons/booking_client.png', width: 18, height: 18),
                    const SizedBox(width: 8),
                    Text(_tr('Bron qilish', 'Bron qilish')),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
    }).toList();
  }

  Widget _factRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: _textMuted, fontSize: 12)),
          const SizedBox(height: 2),
          Text(
            value,
            style: const TextStyle(fontWeight: FontWeight.w600),
            softWrap: true,
          ),
        ],
      ),
    );
  }

  String _roomTypeLabel(String? raw) {
    final s = (raw ?? '').toLowerCase();
    if (s.contains('family') || s.contains('oil')) return _tr('Oilaviy', 'Oilaviy');
    if (s.contains('bed') || s.contains('kravat') || s.contains('кров')) return _tr('Kravatli', 'Kravatli');
    if (raw == null || raw.trim().isEmpty) return _tr('Boshqa', 'Boshqa');
    return raw;
  }

  String _bookingModeLabel(String? raw) {
    final s = (raw ?? '').toLowerCase();
    if (s == 'full') return _tr('To\'liq xona', 'To\'liq xona');
    return _tr('Kravat bo\'yicha', 'Kravat bo\'yicha');
  }

  String _occupancyLabel(String? raw) {
    final s = (raw ?? '').toLowerCase();
    if (s.contains('full')) return _tr('To\'liq band', 'To\'liq band');
    if (s.contains('partial')) return _tr('Qisman band', 'Qisman band');
    return _tr('Bo\'sh', 'Bo\'sh');
  }

  String _bedBreakdown(RoomSummary r) {
    final total = r.bedCount ?? 0;
    final single = r.singleCount ?? 0;
    final dbl = r.doubleCount ?? 0;
    final child = r.childCount ?? 0;
    return '$total (${_tr("Bir kishilik", "Bir kishilik")}: $single, '
        '${_tr("Ikki kishilik", "Ikki kishilik")}: $dbl, '
        '${_tr("Bolalar", "Bolalar")}: $child)';
  }

  Future<void> _openBooking(RoomSummary room) async {
    if (_branch == null) return;
    final roomLabel = room.roomName ?? room.roomNumber ?? '';
    final rentType = _bookingModeLabel(room.bookingMode);
    final display = roomLabel.isEmpty ? rentType : '$roomLabel ($rentType)';
    if (!mounted) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => BookingRequestScreen(
          lang: widget.lang,
          branchId: _branch!.id,
          branchName: _branch!.name,
          prepayLabel: _branch!.prepayLabel(widget.lang),
          roomLabel: display,
          roomType: _roomTypeLabel(room.roomType),
          rentType: rentType,
        ),
      ),
    );
  }
}

class BookingRequestScreen extends StatefulWidget {
  const BookingRequestScreen({
    super.key,
    required this.lang,
    required this.branchId,
    required this.branchName,
    this.prepayLabel,
    this.roomLabel,
    this.roomType,
    this.rentType,
  });

  final String lang;
  final int branchId;
  final String branchName;
  final String? prepayLabel;
  final String? roomLabel;
  final String? roomType;
  final String? rentType;

  @override
  State<BookingRequestScreen> createState() => _BookingRequestScreenState();
}

class _BookingRequestScreenState extends State<BookingRequestScreen> {
  final _nameCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _roomCtrl = TextEditingController();
  final _checkinCtrl = TextEditingController();
  final _checkoutCtrl = TextEditingController();
  final _msgCtrl = TextEditingController();
  bool _busy = false;
  bool _isHourly = false;

  String _tr(String ru, String uz) => widget.lang == 'ru' ? ru : uz;

  @override
  void initState() {
    super.initState();
    _roomCtrl.text = widget.roomLabel ?? '';
    _loadEmail();
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _phoneCtrl.dispose();
    _emailCtrl.dispose();
    _roomCtrl.dispose();
    _checkinCtrl.dispose();
    _checkoutCtrl.dispose();
    _msgCtrl.dispose();
    super.dispose();
  }

  Future<void> _loadEmail() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final email = prefs.getString('client_email') ?? '';
      if (email.isNotEmpty) {
        setState(() => _emailCtrl.text = email);
      }
    } catch (_) {}
  }

  Future<void> _pickDate(TextEditingController ctrl) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: now,
      firstDate: now.subtract(const Duration(days: 0)),
      lastDate: now.add(const Duration(days: 365)),
    );
    if (picked != null) {
      ctrl.text = '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
    }
  }

  Future<void> _submit() async {
    final phone = _phoneCtrl.text.trim();
    if (phone.isEmpty) {
      _showSnack(_tr('Телефон обязателен', 'Telefon majburiy'), error: true);
      return;
    }
    if (!_isHourly) {
      if (_checkinCtrl.text.trim().isEmpty || _checkoutCtrl.text.trim().isEmpty) {
        _showSnack(_tr('Введите даты заезда и выезда', 'Kelish va ketish sanasini kiriting'), error: true);
        return;
      }
    }
    setState(() => _busy = true);
    try {
      final payload = {
        'branch_id': widget.branchId,
        'full_name': _nameCtrl.text.trim().isEmpty ? null : _nameCtrl.text.trim(),
        'phone': phone,
        'email': _emailCtrl.text.trim().isEmpty ? null : _emailCtrl.text.trim(),
        'room_or_bed': _roomCtrl.text.trim().isEmpty ? null : _roomCtrl.text.trim(),
        'checkin': _checkinCtrl.text.trim().isEmpty ? null : _checkinCtrl.text.trim(),
        'checkout': _checkoutCtrl.text.trim().isEmpty ? null : _checkoutCtrl.text.trim(),
        'message': _msgCtrl.text.trim().isEmpty ? null : _msgCtrl.text.trim(),
        'source': 'mobile_app',
      };
      final res = await http.post(
        Uri.parse('$_publicApiBase/booking-request'),
        headers: const {'Content-Type': 'application/json'},
        body: jsonEncode(payload),
      );
      if (res.statusCode < 200 || res.statusCode >= 300) {
        _showSnack(_tr('Не удалось отправить заявку', 'Ariza yuborilmadi'), error: true);
        return;
      }
      _showSnack(_tr('Заявка отправлена', 'Ariza yuborildi'));
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      _showSnack(e.toString(), error: true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _showSnack(String msg, {bool error = false}) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(msg),
        backgroundColor: error ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final prepayLabel = widget.prepayLabel ?? '';
    return Scaffold(
      appBar: AppBar(title: Text(_tr('Bron qilish', 'Bron qilish'))),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text(widget.branchName, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
          const SizedBox(height: 10),
          if (prepayLabel.isNotEmpty) ...[
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: const Color(0xFFF0FDF4),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFBBF7D0)),
              ),
              child: Text(
                prepayLabel,
                style: const TextStyle(color: Color(0xFF166534), fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(height: 10),
          ],
          if ((widget.roomType ?? '').isNotEmpty)
            _infoLine(_tr('Xona turi', 'Xona turi'), widget.roomType!),
          if ((widget.rentType ?? '').isNotEmpty)
            _infoLine(_tr('Ijara turi', 'Ijara turi'), widget.rentType!),
          const SizedBox(height: 10),
          TextField(
            controller: _nameCtrl,
            decoration: InputDecoration(
              labelText: _tr('Ism (ixtiyoriy)', 'Ism (ixtiyoriy)'),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _phoneCtrl,
            keyboardType: TextInputType.phone,
            decoration: InputDecoration(
              labelText: _tr('Telefon (majburiy)', 'Telefon (majburiy)'),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _emailCtrl,
            keyboardType: TextInputType.emailAddress,
            decoration: InputDecoration(
              labelText: _tr('Email (ixtiyoriy)', 'Email (ixtiyoriy)'),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _roomCtrl,
            decoration: InputDecoration(
              labelText: _tr('Xona/Yotoq', 'Xona/Yotoq'),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: Row(
                  children: [
                    Switch(
                      value: _isHourly,
                      onChanged: (v) => setState(() => _isHourly = v),
                    ),
                    const SizedBox(width: 6),
                    Text(_tr('Soatlik bron', 'Soatlik bron')),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _checkinCtrl,
                  readOnly: true,
                  onTap: _isHourly ? null : () => _pickDate(_checkinCtrl),
                  decoration: InputDecoration(
                    labelText: _tr('Kelish sanasi', 'Kelish sanasi'),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: TextField(
                  controller: _checkoutCtrl,
                  readOnly: true,
                  onTap: _isHourly ? null : () => _pickDate(_checkoutCtrl),
                  decoration: InputDecoration(
                    labelText: _tr('Ketish sanasi', 'Ketish sanasi'),
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          TextField(
            controller: _msgCtrl,
            maxLines: 3,
            decoration: InputDecoration(
              labelText: _tr('Izoh (ixtiyoriy)', 'Izoh (ixtiyoriy)'),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 16),
          SizedBox(
            height: 48,
            child: FilledButton(
              onPressed: _busy ? null : _submit,
              child: _busy
                  ? Text(_tr('Yuborilmoqda...', 'Yuborilmoqda...'))
                  : Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Image.asset('assets/icons/booking_client.png', width: 18, height: 18),
                        const SizedBox(width: 8),
                        Text(_tr('Yuborish', 'Yuborish')),
                      ],
                    ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _infoLine(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          Text('$label: ', style: const TextStyle(color: _textMuted)),
          Expanded(child: Text(value, style: const TextStyle(fontWeight: FontWeight.w600))),
        ],
      ),
    );
  }
}

class RoomSummary {
  RoomSummary({
    this.id,
    this.roomName,
    this.roomNumber,
    this.coverImage,
    this.images = const [],
    this.occupancyStatus,
    this.roomType,
    this.bedCount,
    this.singleCount,
    this.doubleCount,
    this.childCount,
    this.availableBeds,
    this.bookingMode,
    this.roomPriceDaily,
    this.roomPriceHourly,
    this.roomPriceMonthly,
    this.minBedDailyPrice,
    this.maxBedDailyPrice,
    this.minBedHourlyPrice,
    this.maxBedHourlyPrice,
    this.minBedMonthlyPrice,
    this.maxBedMonthlyPrice,
  });

  final int? id;
  final String? roomName;
  final String? roomNumber;
  final String? coverImage;
  final List<String> images;
  final String? occupancyStatus;
  final String? roomType;
  final int? bedCount;
  final int? singleCount;
  final int? doubleCount;
  final int? childCount;
  final int? availableBeds;
  final String? bookingMode;
  final double? roomPriceDaily;
  final double? roomPriceHourly;
  final double? roomPriceMonthly;
  final double? minBedDailyPrice;
  final double? maxBedDailyPrice;
  final double? minBedHourlyPrice;
  final double? maxBedHourlyPrice;
  final double? minBedMonthlyPrice;
  final double? maxBedMonthlyPrice;

  factory RoomSummary.fromJson(Map<String, dynamic> json) {
    double? _num(dynamic v) => v == null ? null : (v is num ? v.toDouble() : double.tryParse(v.toString()));
    int? _int(dynamic v) => v == null ? null : (v is num ? v.toInt() : int.tryParse(v.toString()));
    String? _photo(dynamic v) {
      if (v == null) return null;
      final raw = v.toString();
      if (raw.isEmpty) return null;
      if (raw.startsWith('//')) return 'https:$raw';
      if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
      if (raw.startsWith('/')) return '$_publicHost$raw';
      return '$_publicHost/$raw';
    }
    return RoomSummary(
      id: _int(json['id'] ?? json['room_id']),
      roomName: json['room_name']?.toString(),
      roomNumber: json['room_number']?.toString(),
      coverImage: _photo(json['cover_image'] ?? json['photo']),
      images: (json['images'] as List?)
              ?.map((e) => _photo(e)?.toString())
              .whereType<String>()
              .where((e) => e.isNotEmpty)
              .toList() ??
          const [],
      occupancyStatus: json['occupancy_status']?.toString(),
      roomType: json['room_type']?.toString(),
      bedCount: _int(json['bed_count'] ?? json['total_beds']),
      singleCount: _int(json['single_count'] ?? json['single_beds']),
      doubleCount: _int(json['double_count'] ?? json['double_beds']),
      childCount: _int(json['child_count'] ?? json['child_beds']),
      availableBeds: _int(json['available_beds']),
      bookingMode: json['booking_mode']?.toString(),
      roomPriceDaily: _num(json['room_price_daily']),
      roomPriceHourly: _num(json['room_price_hourly']),
      roomPriceMonthly: _num(json['room_price_monthly']),
      minBedDailyPrice: _num(json['min_bed_daily_price']),
      maxBedDailyPrice: _num(json['max_bed_daily_price']),
      minBedHourlyPrice: _num(json['min_bed_hourly_price']),
      maxBedHourlyPrice: _num(json['max_bed_hourly_price']),
      minBedMonthlyPrice: _num(json['min_bed_monthly_price']),
      maxBedMonthlyPrice: _num(json['max_bed_monthly_price']),
    );
  }
}

class _RoomPriceTabs extends StatefulWidget {
  const _RoomPriceTabs({
    required this.roomDaily,
    required this.roomHourly,
    required this.roomMonthly,
    required this.bedDaily,
    required this.bedHourly,
    required this.bedMonthly,
    required this.lang,
  });

  final String roomDaily;
  final String roomHourly;
  final String roomMonthly;
  final String bedDaily;
  final String bedHourly;
  final String bedMonthly;
  final String lang;

  @override
  State<_RoomPriceTabs> createState() => _RoomPriceTabsState();
}

class _RoomPriceTabsState extends State<_RoomPriceTabs> {
  String _tab = 'room';

  String _tr(String ru, String uz) => widget.lang == 'ru' ? ru : uz;

  String _label(String mode) {
    if (mode == 'hour') return _tr('Soatlik', 'Soatlik');
    if (mode == 'month') return _tr('Oylik', 'Oylik');
    return _tr('Kunlik', 'Kunlik');
  }

  Widget _priceRow(String label, String value) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: _border),
      ),
      child: Row(
        children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 12, color: _textMuted))),
          const SizedBox(width: 8),
          Text(value, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            color: const Color(0xFFF1F5F9),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Row(
            children: [
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _tab = 'room'),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    decoration: BoxDecoration(
                      color: _tab == 'room' ? Colors.white : Colors.transparent,
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: _tab == 'room'
                          ? const [BoxShadow(color: Color(0x22000000), blurRadius: 6, offset: Offset(0, 2))]
                          : const [],
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _tr('Xona narxi', 'Xona narxi'),
                      style: TextStyle(fontWeight: FontWeight.w600, color: _tab == 'room' ? _brandBlue : _textMuted),
                    ),
                  ),
                ),
              ),
              Expanded(
                child: GestureDetector(
                  onTap: () => setState(() => _tab = 'bed'),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 150),
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    decoration: BoxDecoration(
                      color: _tab == 'bed' ? Colors.white : Colors.transparent,
                      borderRadius: BorderRadius.circular(10),
                      boxShadow: _tab == 'bed'
                          ? const [BoxShadow(color: Color(0x22000000), blurRadius: 6, offset: Offset(0, 2))]
                          : const [],
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      _tr('Kravat narxi', 'Kravat narxi'),
                      style: TextStyle(fontWeight: FontWeight.w600, color: _tab == 'bed' ? _brandBlue : _textMuted),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        if (_tab == 'room') ...[
          _priceRow(_label("day"), widget.roomDaily),
          _priceRow(_label("hour"), widget.roomHourly),
          _priceRow(_label("month"), widget.roomMonthly),
        ] else ...[
          _priceRow(_label("day"), widget.bedDaily),
          _priceRow(_label("hour"), widget.bedHourly),
          _priceRow(_label("month"), widget.bedMonthly),
        ],
      ],
    );
  }
}










