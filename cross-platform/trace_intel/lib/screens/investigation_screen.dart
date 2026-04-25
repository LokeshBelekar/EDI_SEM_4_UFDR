import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class InvestigationScreen extends StatefulWidget {
  const InvestigationScreen({super.key});

  @override
  State<InvestigationScreen> createState() => _InvestigationScreenState();
}

class _InvestigationScreenState extends State<InvestigationScreen> {
  final TextEditingController _queryController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  final FocusNode _inputFocusNode = FocusNode();

  List<Map<String, dynamic>> _chatLog = [];
  bool _isProcessing = false;
  String? _lastFetchedCase;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    if (selectedCase != null && selectedCase != _lastFetchedCase) {
      _loadHistory(selectedCase);
    } else if (selectedCase == null && _chatLog.isNotEmpty) {
      setState(() {
        _chatLog = [];
        _lastFetchedCase = null;
      });
    }
  }

  @override
  void dispose() {
    _queryController.dispose();
    _scrollController.dispose();
    _inputFocusNode.dispose();
    super.dispose();
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  Future<void> _loadHistory(String caseId) async {
    setState(() {
      _isProcessing = true;
      _lastFetchedCase = caseId;
    });

    try {
      final history = await apiService.getChatHistory(caseId);
      final formattedHistory = history.map((msg) {
        return {
          'role': msg['role'],
          'content': msg['content'] ?? '',
          'intent': msg['role'] == 'ai' ? 'AUTONOMOUS_AGENT' : null,
          'entities': <String, dynamic>{},
          'timestamp': msg['timestamp'] ?? _getCurrentTime(),
        };
      }).toList();

      setState(() {
        _chatLog = formattedHistory;
      });
      _scrollToBottom();
    } catch (e) {
      debugPrint("Failed to load history: $e");
      setState(() => _chatLog = []);
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleClearMemory() async {
    final selectedCase = context.read<CaseProvider>().selectedCase;
    if (selectedCase == null || _isProcessing) return;

    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text("Clear Case Memory?", style: TextStyle(color: AppTheme.dangerRed)),
        content: const Text("This will permanently wipe the AI Agent's conversation history for this case. This action cannot be undone."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text("CANCEL")),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: AppTheme.dangerRed),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text("WIPE MEMORY", style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    if (confirm != true) return;

    setState(() => _isProcessing = true);
    try {
      await apiService.clearCaseMemory(selectedCase);
      setState(() => _chatLog.clear());
    } catch (e) {
      debugPrint("Failed to clear memory: $e");
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  Future<void> _handleSubmit() async {
    final selectedCase = context.read<CaseProvider>().selectedCase;
    final query = _queryController.text.trim();
    if (query.isEmpty || selectedCase == null || _isProcessing) return;

    final userMessage = {
      'role': 'user',
      'content': query,
      'timestamp': _getCurrentTime(),
    };

    setState(() {
      _chatLog.add(userMessage);
      _queryController.clear();
      _isProcessing = true;
    });
    _scrollToBottom();

    try {
      final response = await apiService.queryForensicAI(selectedCase, query);
      
      final aiMessage = {
        'role': 'ai',
        'intent': response['intent_detected'] ?? 'ANALYSIS',
        'content': response['forensic_report'] ?? 'No report generated.',
        'entities': response['entities_extracted'] ?? {},
        'timestamp': _getCurrentTime(),
      };

      setState(() => _chatLog.add(aiMessage));
    } catch (e) {
      setState(() {
        _chatLog.add({
          'role': 'error',
          'content': 'CRITICAL COMM FAILURE: Agent Engine unreachable or Context Timeout.',
          'timestamp': _getCurrentTime(),
        });
      });
    } finally {
      setState(() => _isProcessing = false);
      _scrollToBottom();
      _inputFocusNode.requestFocus(); // Keep focus for rapid typing
    }
  }

  String _getCurrentTime() {
    final now = DateTime.now();
    return "${now.hour.toString().padLeft(2, '0')}:${now.minute.toString().padLeft(2, '0')}:${now.second.toString().padLeft(2, '0')}";
  }

  @override
  Widget build(BuildContext context) {
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    // Detect mobile width to compress UI
    final isMobile = MediaQuery.of(context).size.width < 600;

    if (selectedCase == null) {
      return _buildEmptyState(isMobile);
    }

    return Column(
      children: [
        _buildHeader(selectedCase, isMobile),
        Expanded(
          child: Container(
            color: AppTheme.bgLight,
            child: _buildChatDisplay(isMobile),
          ),
        ),
        _buildInputArea(isMobile),
      ],
    );
  }

  Widget _buildEmptyState(bool isMobile) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.terminal, size: 64, color: AppTheme.borderLight),
            const SizedBox(height: 24),
            Text(
              'Awaiting Case Context',
              textAlign: TextAlign.center,
              style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
                fontSize: isMobile ? 20 : 24, 
                color: AppTheme.primaryNavy
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Initialize investigative terminal by selecting a Case ID from the repository.',
              textAlign: TextAlign.center,
              style: AppTheme.lightTheme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(String caseId, bool isMobile) {
    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: isMobile ? 16 : 32, 
        vertical: isMobile ? 12 : 20
      ),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceWhite,
        border: Border(bottom: BorderSide(color: AppTheme.borderLight)),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'TERMINAL SESSION ACTIVE',
                  style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
                    color: AppTheme.accentTeal,
                    fontSize: isMobile ? 8 : 10,
                    letterSpacing: 1.5,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'INVESTIGATION: ${caseId.toUpperCase()}',
                  style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
                    fontSize: isMobile ? 14 : 18,
                    color: AppTheme.primaryNavy,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Row(
            children: [
              if (!isMobile) // Hide complex badges on mobile to save space
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    border: Border.all(color: AppTheme.borderLight),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    'SECURE_TUNNEL: AES-256',
                    style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10, color: AppTheme.textMuted),
                  ),
                ),
              if (!isMobile) const SizedBox(width: 16),
              OutlinedButton.icon(
                onPressed: _isProcessing ? null : _handleClearMemory,
                icon: Icon(Icons.delete_sweep, size: isMobile ? 18 : 16),
                label: Text(isMobile ? 'RESET' : 'RESET BUFFER'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: AppTheme.dangerRed,
                  side: const BorderSide(color: AppTheme.dangerRed),
                  padding: isMobile ? const EdgeInsets.symmetric(horizontal: 12, vertical: 8) : null,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildChatDisplay(bool isMobile) {
    return ListView.builder(
      controller: _scrollController,
      padding: EdgeInsets.all(isMobile ? 16 : 32),
      itemCount: _chatLog.length + (_isProcessing ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == 0 && _chatLog.isEmpty && !_isProcessing) {
          return _buildIntroBanner(isMobile);
        }

        if (index == _chatLog.length && _isProcessing) {
          return _buildProcessingIndicator();
        }

        final msg = _chatLog[index];
        if (msg['role'] == 'user') return _buildUserMessage(msg, isMobile);
        if (msg['role'] == 'ai') return _buildAiMessage(msg, isMobile);
        return _buildErrorMessage(msg);
      },
    );
  }

  Widget _buildIntroBanner(bool isMobile) {
    return Container(
      margin: const EdgeInsets.only(bottom: 32),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: AppTheme.secondaryBlue.withOpacity(0.05),
        border: Border.all(color: AppTheme.secondaryBlue.withOpacity(0.2)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'TraceIntel Autonomous Agent v5.0.0',
            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
              color: AppTheme.secondaryBlue,
              fontWeight: FontWeight.bold,
              fontSize: isMobile ? 12 : 14,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'READY FOR INPUT. QUERY AUTONOMOUS AGENT FOR RELATIONAL OR BEHAVIORAL PATTERNS.',
            style: TextStyle(color: AppTheme.textMuted, fontSize: isMobile ? 10 : 12),
          ),
        ],
      ),
    );
  }

  Widget _buildUserMessage(Map<String, dynamic> msg, bool isMobile) {
    return Align(
      alignment: Alignment.centerRight,
      child: Container(
        // Dynamic margins so text isn't squished on phones
        margin: EdgeInsets.only(bottom: 24, left: isMobile ? 32 : 100),
        padding: EdgeInsets.all(isMobile ? 12 : 16),
        decoration: BoxDecoration(
          color: AppTheme.secondaryBlue.withOpacity(0.05),
          border: const Border(right: BorderSide(color: AppTheme.secondaryBlue, width: 3)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Text(
              r'INVESTIGATOR@LOCAL:~$',
              style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.secondaryBlue, fontSize: 10),
            ),
            const SizedBox(height: 8),
            Text(msg['content'], style: const TextStyle(color: AppTheme.textMain)),
          ],
        ),
      ),
    );
  }

  Widget _buildAiMessage(Map<String, dynamic> msg, bool isMobile) {
    final Map<String, dynamic> entities = msg['entities'] ?? {};
    
    return Container(
      // Dynamic margins so text isn't squished on phones
      margin: EdgeInsets.only(bottom: 32, right: isMobile ? 16 : 100),
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite,
        borderRadius: BorderRadius.circular(8),
        boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 10, offset: const Offset(0, 4))],
        border: Border.all(color: AppTheme.borderLight),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppTheme.borderLight)),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.accentTeal.withOpacity(0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '[${msg['intent']}]',
                    style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.accentTeal, fontSize: 10),
                  ),
                ),
                Text(
                  msg['timestamp'],
                  style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.textMuted, fontSize: 10),
                ),
              ],
            ),
          ),
          
          // Markdown Content
          Padding(
            padding: EdgeInsets.all(isMobile ? 16 : 24),
            child: MarkdownBody(
              data: msg['content'],
              selectable: true,
              styleSheet: MarkdownStyleSheet(
                p: const TextStyle(color: AppTheme.textMain, height: 1.6, fontSize: 14),
                h1: const TextStyle(color: AppTheme.primaryNavy, fontWeight: FontWeight.bold, fontSize: 20),
                h2: const TextStyle(color: AppTheme.primaryNavy, fontWeight: FontWeight.bold, fontSize: 18),
                h3: const TextStyle(color: AppTheme.primaryNavy, fontWeight: FontWeight.bold, fontSize: 16),
                strong: const TextStyle(color: AppTheme.secondaryBlue, fontWeight: FontWeight.bold),
                listBullet: const TextStyle(color: AppTheme.textMuted),
              ),
            ),
          ),

          // Entities Tag Cloud
          if (entities.isNotEmpty && _hasValidEntities(entities)) ...[
            const Divider(height: 1, color: AppTheme.borderLight),
            Padding(
              padding: EdgeInsets.all(isMobile ? 16 : 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'EXTRACTED_ENTITIES:',
                    style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.textMuted, fontSize: 10),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: entities.entries.where((e) => e.value != null && e.value.toString().isNotEmpty && (e.value is! List || e.value.isNotEmpty)).map((e) {
                      String displayVal = e.value is List ? (e.value as List).join(', ') : e.value.toString();
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: AppTheme.bgLight,
                          border: Border.all(color: AppTheme.borderLight),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: RichText(
                          text: TextSpan(
                            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10),
                            children: [
                              TextSpan(text: '${e.key.toUpperCase()}: ', style: const TextStyle(color: AppTheme.secondaryBlue)),
                              TextSpan(text: displayVal, style: const TextStyle(color: AppTheme.textMain)),
                            ],
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ]
        ],
      ),
    );
  }

  bool _hasValidEntities(Map<String, dynamic> entities) {
    for (var val in entities.values) {
      if (val != null && val.toString().isNotEmpty) {
        if (val is List && val.isEmpty) continue;
        return true;
      }
    }
    return false;
  }

  Widget _buildErrorMessage(Map<String, dynamic> msg) {
    return Container(
      margin: const EdgeInsets.only(bottom: 24),
      padding: const EdgeInsets.all(16),
      color: AppTheme.dangerRed.withOpacity(0.1),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: AppTheme.dangerRed),
          const SizedBox(width: 12),
          Expanded(child: Text(msg['content'], style: const TextStyle(color: AppTheme.dangerRed))),
        ],
      ),
    );
  }

  Widget _buildProcessingIndicator() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 16.0),
      child: Row(
        children: [
          const SizedBox(
            width: 16,
            height: 16,
            child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.secondaryBlue),
          ),
          const SizedBox(width: 16),
          Text(
            'ANALYZING EVIDENCE NODES...',
            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.textMuted, fontSize: 10),
          ),
        ],
      ),
    );
  }

  Widget _buildInputArea(bool isMobile) {
    return Container(
      padding: EdgeInsets.all(isMobile ? 12 : 24),
      decoration: const BoxDecoration(
        color: AppTheme.surfaceWhite,
        border: Border(top: BorderSide(color: AppTheme.borderLight)),
      ),
      child: Row(
        children: [
          if (!isMobile) // Hide prompt arrow on mobile to give input more space
            Padding(
              padding: const EdgeInsets.only(right: 16.0),
              child: Text('>', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.secondaryBlue, fontSize: 18)),
            ),
          Expanded(
            child: TextField(
              controller: _queryController,
              focusNode: _inputFocusNode,
              enabled: !_isProcessing,
              style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 14),
              decoration: InputDecoration(
                hintText: isMobile ? "Execute query..." : "Execute query (e.g., 'Identify high-risk communication clusters')...",
                hintStyle: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.textMuted, fontSize: 14),
                border: InputBorder.none,
                isDense: true,
                contentPadding: const EdgeInsets.symmetric(vertical: 8),
              ),
              onSubmitted: (_) => _handleSubmit(),
            ),
          ),
          const SizedBox(width: 8),
          ElevatedButton(
            onPressed: _isProcessing ? null : _handleSubmit,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppTheme.secondaryBlue,
              padding: EdgeInsets.symmetric(
                horizontal: isMobile ? 16 : 24, 
                vertical: isMobile ? 12 : 16
              ),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
            ),
            child: Text(
              _isProcessing ? (isMobile ? 'WAIT' : 'PROCESSING') : (isMobile ? 'SEND' : 'EXECUTE'),
              style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
                color: Colors.white,
                fontSize: isMobile ? 10 : 12,
              ),
            ),
          ),
        ],
      ),
    );
  }
}