import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:flutter_dotenv/flutter_dotenv.dart'; // IMPORT DOTENV

class ApiService {
  // Use a getter to pull the URL from the .env file dynamically.
  // If it's missing, it falls back to the localhost default.
  static String get baseUrl => dotenv.env['BASE_URL'] ?? 'http://127.0.0.1:8000';

  // --- System Endpoints ---
  Future<Map<String, dynamic>> checkHealth() async {
    final response = await http.get(Uri.parse('$baseUrl/health')).timeout(const Duration(seconds: 3));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('System offline');
  }

  // --- Phase 1 to 3 Endpoints ---
  Future<List<String>> getCases() async {
    final response = await http.get(Uri.parse('$baseUrl/api/cases'));
    if (response.statusCode == 200) {
      return List<String>.from(jsonDecode(response.body)['cases']);
    } else throw Exception('Failed to load cases');
  }

  Future<Map<String, dynamic>> getThreatMatrix(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/poi?case_id=$caseId'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load threat matrix');
  }

  // --- Phase 4: Raw Evidence Endpoints ---
  Future<List<dynamic>> getMessages(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/messages'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load messages');
  }

  Future<List<dynamic>> getCalls(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/calls'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load calls');
  }

  Future<List<dynamic>> getContacts(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/contacts'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load contacts');
  }

  Future<List<dynamic>> getTimeline(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/timeline'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load timeline');
  }

  // --- Media Endpoints ---
  Future<List<dynamic>> getMedia(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/media'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load media');
  }

  String getMediaUrl(String caseId, String fileName) {
    return '$baseUrl/api/media/$caseId/$fileName';
  }

  // --- Phase 5: Network Graph Endpoint ---
  Future<Map<String, dynamic>> getNetworkGraph(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/evidence/$caseId/network-graph'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load network graph');
  }

  // --- Phase 6: AI Agent Endpoints ---
  Future<List<dynamic>> getChatHistory(String caseId) async {
    final response = await http.get(Uri.parse('$baseUrl/api/chat/history/$caseId'));
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Failed to load chat history');
  }

  Future<Map<String, dynamic>> queryForensicAI(String caseId, String query) async {
    final response = await http.post(
      Uri.parse('$baseUrl/api/chat'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'case_id': caseId, 'query': query}),
    );
    if (response.statusCode == 200) return jsonDecode(response.body);
    throw Exception('Agent processing failed');
  }

  Future<void> clearCaseMemory(String caseId) async {
    final response = await http.delete(Uri.parse('$baseUrl/api/chat/$caseId'));
    if (response.statusCode != 200) throw Exception('Failed to clear memory');
  }
}

final apiService = ApiService();