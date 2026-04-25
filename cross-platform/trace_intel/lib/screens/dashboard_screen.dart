import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  Map<String, dynamic>? _dashboardData;
  bool _isLoading = false;
  String? _error;
  String? _lastFetchedCase;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    // Re-fetch data if the selected case changes globally
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    if (selectedCase != null && selectedCase != _lastFetchedCase) {
      _fetchDashboardData(selectedCase);
    } else if (selectedCase == null && _dashboardData != null) {
      setState(() {
        _dashboardData = null;
        _lastFetchedCase = null;
      });
    }
  }

  Future<void> _fetchDashboardData(String caseId) async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final data = await apiService.getThreatMatrix(caseId);
      setState(() {
        _dashboardData = data;
        _lastFetchedCase = caseId;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = "DATA_RETRIEVAL_FAILURE: Unable to fetch threat matrix.";
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    final isMobile = MediaQuery.of(context).size.width < 600;

    if (selectedCase == null) {
      return _buildEmptyState();
    }

    return Padding(
      padding: EdgeInsets.all(isMobile ? 16.0 : 32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(selectedCase, isMobile),
          SizedBox(height: isMobile ? 24 : 32),
          Expanded(child: _buildContent(isMobile)),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.screen_search_desktop_outlined, size: 64, color: AppTheme.borderLight),
            const SizedBox(height: 24),
            Text(
              'Awaiting Case Context',
              textAlign: TextAlign.center,
              style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
                fontSize: 24,
                color: AppTheme.primaryNavy,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'Select a target case from the Repository to initialize analysis.',
              textAlign: TextAlign.center,
              style: AppTheme.lightTheme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(String caseId, bool isMobile) {
    final titleWidget = Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'INTELLIGENCE / ANALYTICS / ${caseId.toUpperCase()}',
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMuted,
            fontSize: 10,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Command Dashboard',
          style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
            fontSize: isMobile ? 24 : 28,
            color: AppTheme.primaryNavy,
          ),
        ),
      ],
    );

    final timeWidget = Container(
      margin: EdgeInsets.only(top: isMobile ? 12.0 : 0),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.borderLight),
      ),
      child: Text(
        'LAST SCAN: ${TimeOfDay.now().format(context)}',
        style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
          color: AppTheme.textMuted,
          fontSize: 10,
        ),
      ),
    );

    if (isMobile) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [titleWidget, timeWidget],
      );
    }

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: [titleWidget, timeWidget],
    );
  }

  Widget _buildContent(bool isMobile) {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
    }

    if (_error != null) {
      return Center(
        child: Text(_error!, style: const TextStyle(color: AppTheme.dangerRed)),
      );
    }

    if (_dashboardData == null) {
      return const SizedBox.shrink();
    }

    final rankings = List<dynamic>.from(_dashboardData!['rankings'] ?? []);
    final entityCount = _dashboardData!['entity_count'] ?? 0;

    // Calculate metrics
    final highRiskThreshold = 700.0;
    int highRiskCount = 0;
    int totalMessages = 0;
    Set<String> uniqueIntents = {};

    for (var poi in rankings) {
      final threatScore = (poi['threat_score'] as num?)?.toDouble() ?? 0.0;
      if (threatScore > highRiskThreshold) highRiskCount++;

      final behavioral = poi['risk_indicators']?['behavioral_analysis'] ?? {};
      totalMessages += (behavioral['message_volume'] as num?)?.toInt() ?? 0;

      final intents = List<String>.from(behavioral['detected_intents'] ?? []);
      uniqueIntents.addAll(intents);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Responsive Summary Cards
        _buildResponsiveMetrics(highRiskCount, totalMessages, (entityCount * 1.5).toInt(), uniqueIntents.length, isMobile),
        SizedBox(height: isMobile ? 24 : 32),
        // Data Area
        Expanded(
          child: Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: AppTheme.surfaceWhite,
              border: Border.all(color: AppTheme.borderLight),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: EdgeInsets.all(isMobile ? 16.0 : 24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'POI THREAT MATRIX',
                        style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(fontSize: 16),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'RANKED BY WEIGHTED RISK VECTOR',
                        style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
                          color: AppTheme.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
                const Divider(height: 1, color: AppTheme.borderLight),
                Expanded(
                  child: isMobile 
                      ? _buildMobileRankingList(rankings)
                      : SingleChildScrollView(
                          child: SingleChildScrollView(
                            scrollDirection: Axis.horizontal,
                            child: _buildRankingTable(rankings),
                          ),
                        ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildResponsiveMetrics(int highRiskCount, int totalMessages, int links, int intents, bool isMobile) {
    if (isMobile) {
      // 2x2 Grid for Mobile
      return Column(
        children: [
          Row(
            children: [
              Expanded(child: _buildMetricCard('HIGH RISK', '$highRiskCount', isDanger: highRiskCount > 0, isMobile: isMobile)),
              const SizedBox(width: 12),
              Expanded(child: _buildMetricCard('NODES', '$totalMessages', isMobile: isMobile)),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(child: _buildMetricCard('LINKS', '$links', isMobile: isMobile)),
              const SizedBox(width: 12),
              Expanded(child: _buildMetricCard('INTENTS', '$intents', isMobile: isMobile)),
            ],
          ),
        ],
      );
    }

    // 1x4 Row for Desktop
    return Row(
      children: [
        Expanded(child: _buildMetricCard('HIGH RISK ENTITIES', '$highRiskCount', isDanger: highRiskCount > 0, isMobile: false)),
        const SizedBox(width: 16),
        Expanded(child: _buildMetricCard('TOTAL EVIDENCE NODES', '$totalMessages', isMobile: false)),
        const SizedBox(width: 16),
        Expanded(child: _buildMetricCard('NETWORK LINKS', '$links', isMobile: false)),
        const SizedBox(width: 16),
        Expanded(child: _buildMetricCard('DETECTED INTENTS', '$intents', isMobile: false)),
      ],
    );
  }

  Widget _buildMetricCard(String title, String value, {bool isDanger = false, required bool isMobile}) {
    return Container(
      padding: EdgeInsets.all(isMobile ? 16 : 24),
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite,
        border: Border.all(color: AppTheme.borderLight),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
              color: AppTheme.textMuted,
              fontSize: isMobile ? 9 : 10,
            ),
          ),
          SizedBox(height: isMobile ? 8 : 12),
          Text(
            value,
            style: TextStyle(
              fontSize: isMobile ? 24 : 28,
              fontWeight: FontWeight.bold,
              color: isDanger ? AppTheme.dangerRed : AppTheme.primaryNavy,
            ),
          ),
        ],
      ),
    );
  }

  // --- MOBILE LIST VIEW ---
  Widget _buildMobileRankingList(List<dynamic> rankings) {
    rankings.sort((a, b) => ((b['threat_score'] as num?)?.toDouble() ?? 0.0)
        .compareTo((a['threat_score'] as num?)?.toDouble() ?? 0.0));

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: rankings.length,
      separatorBuilder: (_, __) => const Divider(color: AppTheme.borderLight, height: 32),
      itemBuilder: (context, index) {
        final poi = rankings[index];
        final threatScore = (poi['threat_score'] as num?)?.toDouble() ?? 0.0;
        final isHighRisk = threatScore > 700.0;
        
        final netInfluence = poi['risk_indicators']?['network_influence'] ?? {};
        final behavioral = poi['risk_indicators']?['behavioral_analysis'] ?? {};

        final brokerage = (netInfluence['brokerage_rank'] as num?)?.toDouble() ?? 0.0;
        final msgVol = (behavioral['message_volume'] as num?)?.toInt() ?? 0;
        final scorePercentage = (threatScore / 10).clamp(0, 100);

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(
                  child: Text(
                    poi['entity_name'] ?? 'Unknown',
                    style: TextStyle(
                      fontWeight: isHighRisk ? FontWeight.bold : FontWeight.w600,
                      fontSize: 16,
                      color: isHighRisk ? AppTheme.dangerRed : AppTheme.primaryNavy,
                    ),
                  ),
                ),
                Text(
                  '${scorePercentage.toStringAsFixed(1)}%',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: isHighRisk ? AppTheme.dangerRed : AppTheme.secondaryBlue,
                  ),
                )
              ],
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: scorePercentage / 100,
              backgroundColor: AppTheme.bgLight,
              color: isHighRisk ? AppTheme.dangerRed : AppTheme.secondaryBlue,
              minHeight: 6,
              borderRadius: BorderRadius.circular(3),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _buildMobileChip(Icons.hub, 'Brokerage: ${brokerage.toStringAsFixed(2)}'),
                _buildMobileChip(Icons.chat, 'Msgs: $msgVol'),
              ],
            )
          ],
        );
      },
    );
  }

  Widget _buildMobileChip(IconData icon, String text) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.bgLight,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppTheme.borderLight),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: AppTheme.textMuted),
          const SizedBox(width: 4),
          Text(text, style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10, color: AppTheme.textMain)),
        ],
      ),
    );
  }

  // --- DESKTOP TABLE VIEW ---
  Widget _buildRankingTable(List<dynamic> rankings) {
    // Sort descending by threat score
    rankings.sort((a, b) => ((b['threat_score'] as num?)?.toDouble() ?? 0.0)
        .compareTo((a['threat_score'] as num?)?.toDouble() ?? 0.0));

    return DataTable(
      headingTextStyle: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
        color: AppTheme.textMuted,
        fontSize: 11,
      ),
      dataTextStyle: AppTheme.lightTheme.textTheme.bodyLarge?.copyWith(
        fontSize: 13,
      ),
      columns: const [
        DataColumn(label: Text('ENTITY IDENTIFIER')),
        DataColumn(label: Text('THREAT SCORE')),
        DataColumn(label: Text('BROKERAGE RANK')),
        DataColumn(label: Text('MSG VOLUME')),
        DataColumn(label: Text('INTENT CONFIDENCE')),
      ],
      rows: rankings.map((poi) {
        final threatScore = (poi['threat_score'] as num?)?.toDouble() ?? 0.0;
        final isHighRisk = threatScore > 700.0;
        
        final netInfluence = poi['risk_indicators']?['network_influence'] ?? {};
        final behavioral = poi['risk_indicators']?['behavioral_analysis'] ?? {};

        final brokerage = (netInfluence['brokerage_rank'] as num?)?.toDouble() ?? 0.0;
        final msgVol = (behavioral['message_volume'] as num?)?.toInt() ?? 0;
        final intentConf = (behavioral['intent_confidence_sum'] as num?)?.toDouble() ?? 0.0;

        // 0-1000 scaled to percentage for visual bar
        final scorePercentage = (threatScore / 10).clamp(0, 100);

        return DataRow(
          color: WidgetStateProperty.resolveWith<Color?>((states) {
            if (isHighRisk) return AppTheme.dangerRed.withOpacity(0.05);
            return null;
          }),
          cells: [
            DataCell(Text(
              poi['entity_name'] ?? 'Unknown',
              style: TextStyle(
                fontWeight: isHighRisk ? FontWeight.bold : FontWeight.normal,
                color: isHighRisk ? AppTheme.dangerRed : AppTheme.textMain,
              ),
            )),
            DataCell(Row(
              children: [
                SizedBox(
                  width: 100, // Fixed width so progress bars align cleanly
                  child: LinearProgressIndicator(
                    value: scorePercentage / 100,
                    backgroundColor: AppTheme.borderLight,
                    color: isHighRisk ? AppTheme.dangerRed : AppTheme.secondaryBlue,
                    minHeight: 6,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(width: 12),
                SizedBox(
                  width: 50,
                  child: Text(
                    '${scorePercentage.toStringAsFixed(1)}%',
                    style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 12),
                  ),
                ),
              ],
            )),
            DataCell(Text(brokerage.toStringAsFixed(4), style: AppTheme.lightTheme.textTheme.labelLarge)),
            DataCell(Text(msgVol.toString(), style: AppTheme.lightTheme.textTheme.labelLarge)),
            DataCell(Text(intentConf.toStringAsFixed(2))),
          ],
        );
      }).toList(),
    );
  }
}