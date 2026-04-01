import 'dart:convert';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

const String _publicApiBase = 'https://hmsuz.com/api';
const String _publicHost = 'https://hmsuz.com';
const String _clientLastContactKey = 'client_last_contact';

const Color _bg = Color(0xFFF5F7FB);
const Color _card = Color(0xFFFFFFFF);
const Color _textMuted = Color(0xFF64748B);
const Color _border = Color(0xFFE2E8F0);
const Color _brandBlue = Color(0xFF1D4ED8);
const Color _surfaceSoft = Color(0xFFF7F9FC);

class ClientCatalogScreen extends StatefulWidget {
  const ClientCatalogScreen({super.key, required this.lang});

  final String lang;

  @override
  State<ClientCatalogScreen> createState() => _ClientCatalogScreenState();
}

class _ClientCatalogScreenState extends State<ClientCatalogScreen> {
  final _searchCtrl = TextEditingController();
  bool _loading = false;
  bool _filtersOpen = false;
  bool _filtersActive = false;
  String _priceMode = 'day';
  double _minRating = 0;
  String? _regionSlug;
  String? _cityName;
  String? _districtName;
  String? _roomType;
  RangeValues _priceRange = const RangeValues(0, 0);
  double _priceMinBound = 0;
  double _priceMaxBound = 0;
  List<BranchSummary> _branches = [];
  List<BranchSummary> _filtered = [];
  BookingPrepayConfig? _prepay;
  late String _lang;

  @override
  void initState() {
    super.initState();
    _lang = widget.lang;
    _loadAll();
    _searchCtrl.addListener(_applyClientFilters);
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
  }

  String _tr({required String ru, required String uz}) {
    return _lang == 'ru' ? ru : uz;
  }

  void _setLang(String lang) {
    setState(() {
      _lang = lang == 'ru' ? 'ru' : 'uz';
    });
  }

  Future<void> _loadAll() async {
    await Future.wait([_loadPrepay(), _loadBranches()]);
  }

  Future<void> _loadPrepay() async {
    try {
      final res = await http.get(Uri.parse('$_publicApiBase/public/booking-prepayment'));
      if (res.statusCode != 200) return;
      final payload = jsonDecode(res.body);
      if (payload is Map<String, dynamic>) {
        setState(() {
          _prepay = BookingPrepayConfig.fromJson(payload);
        });
      }
    } catch (_) {}
  }

  Future<void> _loadBranches() async {
    setState(() => _loading = true);
    try {
      final q = <String, String>{
        'limit': '200',
        'price_mode': _priceMode,
      };
      if (_minRating > 0) q['min_rating'] = _minRating.toString();
      if (_roomType != null && _roomType!.trim().isNotEmpty) q['room_type'] = _roomType!;
      if (_regionSlug != null && _regionSlug!.trim().isNotEmpty) q['region_slug'] = _regionSlug!;
      if (_cityName != null && _cityName!.trim().isNotEmpty) q['city_name'] = _cityName!;
      if (_districtName != null && _districtName!.trim().isNotEmpty) q['district_name'] = _districtName!;
      final uri = Uri.parse('$_publicApiBase/public/branches').replace(queryParameters: q);
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode != 200) {
        _showSnack(_tr(ru: 'Не удалось загрузить каталог.', uz: 'Katalogni yuklab bo\'lmadi.'), error: true);
        return;
      }
      final data = jsonDecode(res.body);
      final list = (data as List).map((e) => BranchSummary.fromJson(e as Map<String, dynamic>)).toList();
      _branches = list;
      _recomputePriceBounds();
      _applyClientFilters();
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
    _priceRange = RangeValues(_priceMinBound, _priceMaxBound);
  }

  void _applyClientFilters() {
    final needle = _searchCtrl.text.trim().toLowerCase();
    final min = _priceRange.start;
    final max = _priceRange.end;
    final list = _branches.where((b) {
      if (needle.isNotEmpty) {
        final text = '${b.name} ${b.address ?? ''}'.toLowerCase();
        if (!text.contains(needle)) return false;
      }
      if (_minRating > 0 && (b.rating ?? 0) < _minRating) return false;
      if (_regionSlug != null && _regionSlug!.trim().isNotEmpty && b.regionSlug != _regionSlug) return false;
      if (_cityName != null && _cityName!.trim().isNotEmpty && b.cityName != _cityName) return false;
      if (_districtName != null && _districtName!.trim().isNotEmpty && b.districtName != _districtName) return false;
      if (_roomType != null && _roomType!.trim().isNotEmpty) {
        final parts = b.roomTypes.split(',').map((e) => e.trim()).where((e) => e.isNotEmpty);
        if (!parts.contains(_roomType)) return false;
      }
      final rowMin = b.minPrice;
      final rowMax = b.maxPrice;
      if (rowMin != null || rowMax != null) {
        final a = rowMin ?? rowMax!;
        final c = rowMax ?? rowMin!;
        if (a > max || c < min) return false;
      }
      return true;
    }).toList();
    setState(() {
      _filtered = list;
      _filtersActive = _hasActiveFilters();
    });
  }

  void _toggleFilters() {
    setState(() => _filtersOpen = !_filtersOpen);
  }

  bool _hasActiveFilters() {
    if (_searchCtrl.text.trim().isNotEmpty) return true;
    if (_regionSlug != null && _regionSlug!.trim().isNotEmpty) return true;
    if (_cityName != null && _cityName!.trim().isNotEmpty) return true;
    if (_districtName != null && _districtName!.trim().isNotEmpty) return true;
    if (_roomType != null && _roomType!.trim().isNotEmpty) return true;
    if (_priceMode != 'day') return true;
    if (_minRating > 0) return true;
    return false;
  }

  void _resetFilters() {
    setState(() {
      _searchCtrl.clear();
      _priceMode = 'day';
      _minRating = 0;
      _regionSlug = null;
      _cityName = null;
      _districtName = null;
      _roomType = null;
      _priceRange = RangeValues(_priceMinBound, _priceMaxBound);
      _filtersActive = false;
    });
    _applyClientFilters();
  }

  List<DropdownMenuItem<String?>> _regionItems() {
    final map = <String, String>{};
    for (final b in _branches) {
      final slug = (b.regionSlug ?? '').trim();
      final name = (b.regionName ?? '').trim();
      if (slug.isNotEmpty) map[slug] = name.isEmpty ? slug : name;
    }
    final items = map.entries.toList()..sort((a, b) => a.value.compareTo(b.value));
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все области', uz: 'Barcha viloyatlar'))),
      ...items.map((e) => DropdownMenuItem<String?>(value: e.key, child: Text(e.value))),
    ];
  }

  List<DropdownMenuItem<String?>> _cityItems() {
    final set = <String>{};
    for (final b in _branches) {
      if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
      final name = (b.cityName ?? '').trim();
      if (name.isNotEmpty) set.add(name);
    }
    final list = set.toList()..sort();
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все города', uz: 'Barcha shaharlar'))),
      ...list.map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
    ];
  }

  List<DropdownMenuItem<String?>> _districtItems() {
    final set = <String>{};
    for (final b in _branches) {
      if (_regionSlug != null && _regionSlug!.isNotEmpty && b.regionSlug != _regionSlug) continue;
      if (_cityName != null && _cityName!.isNotEmpty && b.cityName != _cityName) continue;
      final name = (b.districtName ?? '').trim();
      if (name.isNotEmpty) set.add(name);
    }
    final list = set.toList()..sort();
    return [
      DropdownMenuItem<String?>(value: null, child: Text(_tr(ru: 'Все районы', uz: 'Barcha tumanlar'))),
      ...list.map((e) => DropdownMenuItem<String?>(value: e, child: Text(e))),
    ];
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
      final uri = Uri.parse('$_publicApiBase/public/user-history').replace(queryParameters: {
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
      final uri = Uri.parse('$_publicApiBase/public/branches/$branchId/ratings');
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

  @override
  Widget build(BuildContext context) {
    final rangeMax = max(_priceMaxBound, _priceMinBound + 1);
    final range = RangeValues(
      _priceRange.start.clamp(_priceMinBound, rangeMax),
      _priceRange.end.clamp(_priceMinBound, rangeMax),
    );
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        title: Text(_tr(ru: 'Каталог', uz: 'Katalog')),
        actions: [
          IconButton(
            tooltip: _tr(ru: 'История', uz: 'Tarix'),
            onPressed: _openHistory,
            icon: const Icon(Icons.history),
          ),
          TextButton(
            onPressed: () => _setLang(_lang == 'ru' ? 'uz' : 'ru'),
            child: Text(_lang.toUpperCase()),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
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
                          icon: Image.asset('assets/icons/clear-filter.png', width: 18, height: 18),
                        ),
                  filled: true,
                  fillColor: _card,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: _border)),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(16), borderSide: const BorderSide(color: _border)),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  OutlinedButton.icon(
                    onPressed: _toggleFilters,
                    icon: Image.asset('assets/icons/filter.png', width: 18, height: 18),
                    label: Text(_filtersOpen ? _tr(ru: 'Скрыть', uz: 'Yopish') : _tr(ru: 'Фильтры', uz: 'Filtrlar')),
                  ),
                  const Spacer(),
                  if (_filtersActive)
                    IconButton(
                      onPressed: _resetFilters,
                      tooltip: _tr(ru: 'Сбросить', uz: 'Bekor qilish'),
                      icon: Image.asset('assets/icons/clear-filter.png', width: 18, height: 18),
                    ),
                ],
              ),
            ),
            AnimatedCrossFade(
              crossFadeState: _filtersOpen ? CrossFadeState.showFirst : CrossFadeState.showSecond,
              duration: const Duration(milliseconds: 220),
              firstChild: Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: DropdownButtonFormField<String?>(
                            value: _regionSlug,
                            decoration: InputDecoration(
                              labelText: _tr(ru: 'Область', uz: 'Viloyat'),
                              filled: true,
                              fillColor: _card,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              suffixIcon: _regionSlug == null
                                  ? null
                                  : IconButton(
                                      onPressed: () {
                                        setState(() {
                                          _regionSlug = null;
                                          _cityName = null;
                                          _districtName = null;
                                        });
                                        _applyClientFilters();
                                      },
                                      icon: Image.asset('assets/icons/clear-filter.png', width: 16, height: 16),
                                    ),
                            ),
                            items: _regionItems(),
                            onChanged: (v) {
                              setState(() {
                                _regionSlug = v;
                                _cityName = null;
                                _districtName = null;
                              });
                              _applyClientFilters();
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<String?>(
                            value: _cityName,
                            decoration: InputDecoration(
                              labelText: _tr(ru: 'Город', uz: 'Shahar'),
                              filled: true,
                              fillColor: _card,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              suffixIcon: _cityName == null
                                  ? null
                                  : IconButton(
                                      onPressed: () {
                                        setState(() {
                                          _cityName = null;
                                          _districtName = null;
                                        });
                                        _applyClientFilters();
                                      },
                                      icon: Image.asset('assets/icons/clear-filter.png', width: 16, height: 16),
                                    ),
                            ),
                            items: _cityItems(),
                            onChanged: (v) {
                              setState(() {
                                _cityName = v;
                                _districtName = null;
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
                            decoration: InputDecoration(
                              labelText: _tr(ru: 'Район', uz: 'Tuman'),
                              filled: true,
                              fillColor: _card,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              suffixIcon: _districtName == null
                                  ? null
                                  : IconButton(
                                      onPressed: () {
                                        setState(() => _districtName = null);
                                        _applyClientFilters();
                                      },
                                      icon: Image.asset('assets/icons/clear-filter.png', width: 16, height: 16),
                                    ),
                            ),
                            items: _districtItems(),
                            onChanged: (v) {
                              setState(() => _districtName = v);
                              _applyClientFilters();
                            },
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: DropdownButtonFormField<String?>(
                            value: _roomType,
                            decoration: InputDecoration(
                              labelText: _tr(ru: 'Тип комнаты', uz: 'Xona turi'),
                              filled: true,
                              fillColor: _card,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                              suffixIcon: _roomType == null
                                  ? null
                                  : IconButton(
                                      onPressed: () {
                                        setState(() => _roomType = null);
                                        _applyClientFilters();
                                      },
                                      icon: Image.asset('assets/icons/clear-filter.png', width: 16, height: 16),
                                    ),
                            ),
                            items: _roomTypeItems(),
                            onChanged: (v) {
                              setState(() => _roomType = v);
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
                              labelText: _tr(ru: 'Режим цены', uz: 'Narx turi'),
                              filled: true,
                              fillColor: _card,
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                            ),
                            items: [
                              DropdownMenuItem(value: 'day', child: Text(_tr(ru: 'Сутки', uz: 'Kunlik'))),
                              DropdownMenuItem(value: 'hour', child: Text(_tr(ru: 'Час', uz: 'Soatlik'))),
                              DropdownMenuItem(value: 'month', child: Text(_tr(ru: 'Месяц', uz: 'Oylik'))),
                            ],
                            onChanged: (v) {
                              setState(() => _priceMode = v ?? 'day');
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
                        Text(_tr(ru: 'Диапазон цены', uz: 'Narx oralig\'i')),
                        RangeSlider(
                          min: _priceMinBound,
                          max: rangeMax,
                          values: range,
                          onChanged: (v) {
                            setState(() => _priceRange = v);
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
                  ],
                ),
              ),
              secondChild: const SizedBox.shrink(),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: _loading
                  ? const Center(child: CircularProgressIndicator())
                  : _filtered.isEmpty
                      ? Center(child: Text(_tr(ru: 'Ничего не найдено.', uz: 'Natija topilmadi.')))
                      : ListView.separated(
                          padding: const EdgeInsets.fromLTRB(16, 0, 16, 24),
                          itemCount: _filtered.length,
                          separatorBuilder: (_, __) => const SizedBox(height: 12),
                          itemBuilder: (_, i) => _buildBranchCard(_filtered[i]),
                        ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBranchCard(BranchSummary b) {
    final rating = b.rating != null ? b.rating!.toStringAsFixed(1) : '-';
    final price = b.priceLabel(_priceMode, _lang);
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
          if (b.coverPhoto != null && b.coverPhoto!.trim().isNotEmpty)
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              child: Image.network(
                b.coverPhoto!,
                height: 160,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  height: 160,
                  color: _surfaceSoft,
                  alignment: Alignment.center,
                  child: const Icon(Icons.image_not_supported_outlined),
                ),
              ),
            )
          else
            Container(
              height: 140,
              width: double.infinity,
              decoration: BoxDecoration(
                color: _surfaceSoft,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
              ),
              alignment: Alignment.center,
              child: const Icon(Icons.hotel_outlined, size: 36, color: _textMuted),
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(b.name.isNotEmpty ? b.name : '#${b.id}', style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text(b.address ?? '-', style: const TextStyle(color: _textMuted)),
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
                    const SizedBox(width: 8),
                    if (price.isNotEmpty)
                      Text(price, style: const TextStyle(fontWeight: FontWeight.w600)),
                  ],
                ),
                if (b.roomTypes.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(b.roomTypes, style: const TextStyle(color: _textMuted)),
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
                              prepay: _prepay,
                            ),
                          ),
                        ),
                        child: Text(_tr(ru: 'Подробнее', uz: 'Batafsil')),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: FilledButton(
                        onPressed: () => _openMaps(b),
                        child: Text(_tr(ru: 'Маршрут', uz: 'Yo\'nalish')),
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
    this.roomTypes = '',
    this.coverPhoto,
    this.status,
    this.statusCode,
    this.contactPhone,
    this.contactTelegram,
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
  final String roomTypes;
  final String? coverPhoto;
  final String? status;
  final String? statusCode;
  final String? contactPhone;
  final String? contactTelegram;

  factory BranchSummary.fromJson(Map<String, dynamic> json) {
    double? _num(dynamic v) => v == null ? null : (v is num ? v.toDouble() : double.tryParse(v.toString()));
    String? _photo(dynamic v) {
      if (v == null) return null;
      final raw = v.toString();
      if (raw.isEmpty) return null;
      if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
      if (raw.startsWith('/')) return '$_publicHost$raw';
      return raw;
    }
    return BranchSummary(
      id: (json['id'] is num) ? (json['id'] as num).toInt() : int.tryParse(json['id'].toString()) ?? 0,
      name: (json['name'] ?? '').toString(),
      address: json['address']?.toString(),
      rating: _num(json['rating'] ?? json['avg_rating']),
      ratingCount: (json['rating_count'] is num) ? (json['rating_count'] as num).toInt() : null,
      minPrice: _num(json['min_price'] ?? json['minPrice']),
      maxPrice: _num(json['max_price'] ?? json['maxPrice']),
      latitude: _num(json['latitude'] ?? json['lat']),
      longitude: _num(json['longitude'] ?? json['lng']),
      regionSlug: json['region_slug']?.toString(),
      regionName: json['region_name']?.toString(),
      cityName: json['city_name']?.toString(),
      districtName: json['district_name']?.toString(),
      roomTypes: (json['room_types'] ?? json['roomTypes'] ?? '').toString(),
      coverPhoto: _photo(json['cover_photo'] ?? json['coverPhoto'] ?? json['photo']),
      status: json['status']?.toString(),
      statusCode: json['status_code']?.toString(),
      contactPhone: json['contact_phone']?.toString(),
      contactTelegram: json['contact_telegram']?.toString(),
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
    if (note != null && note!.trim().isNotEmpty) return note!;
    if (amount != null) {
      return lang == 'ru' ? 'Предоплата: ${amount!.toStringAsFixed(0)}' : 'Oldindan to\'lov: ${amount!.toStringAsFixed(0)}';
    }
    return lang == 'ru' ? 'Предоплата требуется' : 'Oldindan to\'lov talab qilinadi';
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

class ClientBranchDetailsScreen extends StatefulWidget {
  const ClientBranchDetailsScreen({
    super.key,
    required this.lang,
    required this.branchId,
    this.prepay,
  });

  final String lang;
  final int branchId;
  final BookingPrepayConfig? prepay;

  @override
  State<ClientBranchDetailsScreen> createState() => _ClientBranchDetailsScreenState();
}

class _ClientBranchDetailsScreenState extends State<ClientBranchDetailsScreen> {
  BranchSummary? _details;
  bool _loading = true;
  List<String> _photos = [];

  String _tr(String ru, String uz) => widget.lang == 'ru' ? ru : uz;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final uri = Uri.parse('$_publicApiBase/public/branches/${widget.branchId}/details');
      final res = await http.get(uri, headers: const {'Cache-Control': 'no-cache'});
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        if (data is Map<String, dynamic>) {
          _details = BranchSummary.fromJson(data);
        }
      }
      final photosUri = Uri.parse('$_publicApiBase/public/branches/${widget.branchId}/photos');
      final photosRes = await http.get(photosUri, headers: const {'Cache-Control': 'no-cache'});
      if (photosRes.statusCode == 200) {
        final photosData = jsonDecode(photosRes.body);
        final list = photosData is List ? photosData : (photosData is Map ? photosData['items'] : null);
        if (list is List) {
          _photos = list.map((e) {
            if (e is Map && e['url'] != null) return e['url'].toString();
            if (e is Map && e['photo'] != null) return e['photo'].toString();
            return e.toString();
          }).where((e) => e.trim().isNotEmpty).toList();
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
          : _details == null
              ? Center(child: Text(_tr('Не удалось загрузить.', 'Yuklab bo\'lmadi.')))
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    Text(_details!.name, style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 6),
                    Text(_details!.address ?? '-', style: const TextStyle(color: _textMuted)),
                    const SizedBox(height: 10),
                    Wrap(
                      spacing: 8,
                      runSpacing: 8,
                      children: [
                        _infoChip('⭐ ${_details!.rating?.toStringAsFixed(1) ?? '-'}'),
                        if (_details!.roomTypes.isNotEmpty) _infoChip(_details!.roomTypes),
                        if (_details!.minPrice != null || _details!.maxPrice != null)
                          _infoChip(_details!.priceLabel('day', widget.lang)),
                      ],
                    ),
                    if (widget.prepay != null && widget.prepay!.enabled) ...[
                      const SizedBox(height: 8),
                      Text(widget.prepay!.label(widget.lang), style: const TextStyle(color: _textMuted)),
                    ],
                    const SizedBox(height: 14),
                    if (_photos.isNotEmpty)
                      SizedBox(
                        height: 160,
                        child: ListView.separated(
                          scrollDirection: Axis.horizontal,
                          itemCount: _photos.length,
                          separatorBuilder: (_, __) => const SizedBox(width: 10),
                          itemBuilder: (_, i) => ClipRRect(
                            borderRadius: BorderRadius.circular(12),
                            child: Image.network(
                              _photos[i],
                              width: 220,
                              height: 160,
                              fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => Container(
                                width: 220,
                                color: _surfaceSoft,
                                alignment: Alignment.center,
                                child: const Icon(Icons.image_not_supported_outlined),
                              ),
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Expanded(
                          child: OutlinedButton(
                            onPressed: _details!.contactPhone == null || _details!.contactPhone!.isEmpty
                                ? null
                                : () => _launchPhone(_details!.contactPhone!),
                            child: Text(_tr('Позвонить', 'Qo\'ng\'iroq')),
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: FilledButton(
                            onPressed: () => _openMaps(_details!),
                            child: Text(_tr('Открыть карту', 'Xaritani ochish')),
                          ),
                        ),
                      ],
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
}
