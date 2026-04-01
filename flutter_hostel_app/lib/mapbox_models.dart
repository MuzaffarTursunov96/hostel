class MapPoint {
  MapPoint({
    required this.lat,
    required this.lng,
    required this.name,
    required this.rating,
    required this.status,
    required this.statusCode,
  });
  final double lat;
  final double lng;
  final String name;
  final double rating;
  final String status;
  final String statusCode;
}
