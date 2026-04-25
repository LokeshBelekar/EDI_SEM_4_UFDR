import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class CaseExplorerScreen extends StatefulWidget {
  const CaseExplorerScreen({super.key});

  @override
  State<CaseExplorerScreen> createState() => _CaseExplorerScreenState();
}

class _CaseExplorerScreenState extends State<CaseExplorerScreen> {
  List<String> _cases = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadCases();
  }

  Future<void> _loadCases() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final cases = await apiService.getCases();
      setState(() {
        _cases = cases;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = "FAILED TO ACCESS ARCHIVE: Connection to Case Management Service lost.";
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    // Detect if we are on a mobile-sized screen
    final isMobile = MediaQuery.of(context).size.width < 600;

    return Padding(
      // Dynamic padding to save screen real estate on mobile
      padding: EdgeInsets.all(isMobile ? 16.0 : 32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(isMobile),
          SizedBox(height: isMobile ? 24 : 32),
          Expanded(child: _buildContent(isMobile)),
        ],
      ),
    );
  }

  Widget _buildHeader(bool isMobile) {
    final titleWidget = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'SYSTEM / ARCHIVE / VOLUMES',
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMuted,
            fontSize: 10,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Case Repository',
          style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
            fontSize: isMobile ? 24 : 28,
            color: AppTheme.primaryNavy,
          ),
        ),
      ],
    );

    final statsBox = Container(
      margin: EdgeInsets.only(top: isMobile ? 16.0 : 0),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite,
        border: Border.all(color: AppTheme.borderLight),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: isMobile ? CrossAxisAlignment.start : CrossAxisAlignment.end,
        children: [
          Text(
            'AVAILABLE VOLUMES',
            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
              color: AppTheme.textMuted,
              fontSize: 10,
            ),
          ),
          Text(
            '${_cases.length}',
            style: const TextStyle(
              fontSize: 20,
              fontWeight: FontWeight.bold,
              color: AppTheme.secondaryBlue,
            ),
          ),
        ],
      ),
    );

    // Stack vertically on mobile to prevent overflow, side-by-side on desktop
    if (isMobile) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [titleWidget, statsBox],
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [titleWidget, statsBox],
    );
  }

  Widget _buildContent(bool isMobile) {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppTheme.primaryNavy),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.warning_amber_rounded, color: AppTheme.dangerRed, size: 48),
            const SizedBox(height: 16),
            Text(_error!, style: const TextStyle(color: AppTheme.dangerRed), textAlign: TextAlign.center),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadCases,
              style: ElevatedButton.styleFrom(backgroundColor: AppTheme.primaryNavy),
              child: const Text('RETRY CONNECTION', style: TextStyle(color: Colors.white)),
            ),
          ],
        ),
      );
    }

    if (_cases.isEmpty) {
      return Center(
        child: Text(
          'NO ACTIVE VOLUMES DETECTED IN BACKEND STORAGE.',
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(color: AppTheme.textMuted),
          textAlign: TextAlign.center,
        ),
      );
    }

    // On mobile, use a clean vertical scroll list instead of squishing a Grid
    if (isMobile) {
      return ListView.separated(
        itemCount: _cases.length,
        separatorBuilder: (context, index) => const SizedBox(height: 16),
        itemBuilder: (context, index) {
          return _CaseCard(caseId: _cases[index]);
        },
      );
    }

    // On desktop, keep the multi-column Grid layout
    return GridView.builder(
      gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
        maxCrossAxisExtent: 400,
        mainAxisExtent: 220,
        crossAxisSpacing: 24,
        mainAxisSpacing: 24,
      ),
      itemCount: _cases.length,
      itemBuilder: (context, index) {
        return _CaseCard(caseId: _cases[index]);
      },
    );
  }
}

class _CaseCard extends StatelessWidget {
  final String caseId;

  const _CaseCard({required this.caseId});

  @override
  Widget build(BuildContext context) {
    // Watch the global state to see if this card is the selected case
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    final isActive = selectedCase == caseId;

    return InkWell(
      onTap: () {
        context.read<CaseProvider>().selectCase(caseId);
      },
      borderRadius: BorderRadius.circular(8),
      child: Container(
        height: 220, // Give fixed height so it plays nice inside both ListView and GridView
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: isActive ? AppTheme.secondaryBlue.withOpacity(0.05) : AppTheme.surfaceWhite,
          border: Border.all(
            color: isActive ? AppTheme.secondaryBlue : AppTheme.borderLight,
            width: isActive ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(8),
          boxShadow: isActive
              ? [BoxShadow(color: AppTheme.secondaryBlue.withOpacity(0.2), blurRadius: 8)]
              : [],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.folder_shared,
                  color: isActive ? AppTheme.secondaryBlue : AppTheme.textMuted,
                  size: 28,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'CASE IDENTIFIER',
                        style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
                          color: AppTheme.textMuted,
                          fontSize: 10,
                        ),
                      ),
                      Text(
                        caseId,
                        style: const TextStyle(
                          fontWeight: FontWeight.bold,
                          fontSize: 16,
                          color: AppTheme.primaryNavy,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Spacer(),
            _buildDataPoint('CLASSIFICATION', 'UNCLASSIFIED_LEO'),
            const SizedBox(height: 8),
            _buildDataPoint('PROCESSING CORE', 'LANGCHAIN_AGENT_v5'),
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                onPressed: isActive ? null : () => context.read<CaseProvider>().selectCase(caseId),
                style: ElevatedButton.styleFrom(
                  backgroundColor: isActive ? AppTheme.borderLight : AppTheme.primaryNavy,
                  foregroundColor: isActive ? AppTheme.textMuted : Colors.white,
                  elevation: 0,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
                ),
                child: Text(isActive ? 'AGENT CONTEXT ACTIVE' : 'INITIALIZE AGENT', style: const TextStyle(fontSize: 12, letterSpacing: 0.5)),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDataPoint(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMuted,
            fontSize: 9,
          ),
        ),
        Text(
          value,
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMain,
            fontSize: 9,
          ),
        ),
      ],
    );
  }
}