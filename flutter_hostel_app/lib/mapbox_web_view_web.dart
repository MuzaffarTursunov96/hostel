import 'dart:convert';
import 'dart:html' as html;
import 'dart:js' as js;
import 'dart:ui' as ui;

import 'package:flutter/widgets.dart';
import 'package:latlong2/latlong.dart';

import 'mapbox_models.dart';

Widget mapboxWebView({
  required LatLng center,
  required List<MapPoint> points,
  required String token,
  required String styleUri,
}) {
  final viewId = 'mapbox-view-${DateTime.now().microsecondsSinceEpoch}';
  final element = html.DivElement()
    ..id = viewId
    ..style.width = '100%'
    ..style.height = '100%';

  // ignore: undefined_prefixed_name
  ui.platformViewRegistry.registerViewFactory(viewId, (int _) => element);

  WidgetsBinding.instance.addPostFrameCallback((_) {
    final markers = points
        .map((p) => {
              'lat': p.lat,
              'lng': p.lng,
              'name': p.name,
              'rating': p.rating,
              'status': p.status,
              'statusCode': p.statusCode,
            })
        .toList();
    final markersJson = jsonEncode(markers);
    js.context.callMethod(
      'createMapboxMap',
      [viewId, token, center.latitude, center.longitude, markersJson, styleUri],
    );
  });

  return HtmlElementView(viewType: viewId);
}
