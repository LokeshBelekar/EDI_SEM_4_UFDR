import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class CaseProvider extends ChangeNotifier {
  String? _selectedCase;
  static const String _storageKey = 'active_case_id';

  String? get selectedCase => _selectedCase;

  CaseProvider() {
    _loadPersistedCase();
  }

  // Replaces the React useEffect localStorage logic
  Future<void> _loadPersistedCase() async {
    final prefs = await SharedPreferences.getInstance();
    _selectedCase = prefs.getString(_storageKey);
    notifyListeners();
  }

  Future<void> selectCase(String caseId) async {
    _selectedCase = caseId;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_storageKey, caseId);
    notifyListeners();
  }

  Future<void> clearCase() async {
    _selectedCase = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_storageKey);
    notifyListeners();
  }
}