import 'dart:async';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class MainLayout extends StatelessWidget {
  final Widget child;

  const MainLayout({super.key, required this.child});

  int _getSelectedIndex(BuildContext context) {
    final String location = GoRouterState.of(context).uri.toString();
    if (location.startsWith('/cases')) return 0;
    if (location.startsWith('/dashboard')) return 1;
    if (location.startsWith('/evidence')) return 2;
    if (location.startsWith('/graph')) return 3;
    if (location.startsWith('/investigation')) return 4;
    return 0;
  }

  void _onItemTapped(int index, BuildContext context) {
    switch (index) {
      case 0: context.go('/cases'); break;
      case 1: context.go('/dashboard'); break;
      case 2: context.go('/evidence'); break;
      case 3: context.go('/graph'); break;
      case 4: context.go('/investigation'); break;
    }
  }

  @override
  Widget build(BuildContext context) {
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    final currentIndex = _getSelectedIndex(context);
    final bool isMobile = MediaQuery.of(context).size.width < 600;

    return Scaffold(
      backgroundColor: AppTheme.bgLight,
      appBar: AppBar(
        title: Row(
          children: [
            const Icon(Icons.shield, color: AppTheme.accentTeal),
            const SizedBox(width: 12),
            const Text('TraceIntel', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1)),
          ],
        ),
        actions: [
          // NEW: Live Server Health Indicator
          const _SystemHealthWidget(),
          
          Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
            decoration: BoxDecoration(
              color: selectedCase == null ? AppTheme.dangerRed.withOpacity(0.1) : AppTheme.secondaryBlue.withOpacity(0.1),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: selectedCase == null ? AppTheme.dangerRed : AppTheme.secondaryBlue),
            ),
            child: Row(
              children: [
                Icon(
                  Icons.folder_shared, 
                  size: 16, 
                  color: selectedCase == null ? AppTheme.dangerRed : AppTheme.secondaryBlue
                ),
                const SizedBox(width: 8),
                Text(
                  selectedCase ?? 'NO CASE',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                    color: selectedCase == null ? AppTheme.dangerRed : AppTheme.primaryNavy,
                  ),
                ),
              ],
            ),
          )
        ],
      ),
      body: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth >= 600) {
            return Row(
              children: [
                NavigationRail(
                  selectedIndex: currentIndex,
                  onDestinationSelected: (idx) => _onItemTapped(idx, context),
                  labelType: NavigationRailLabelType.all,
                  backgroundColor: AppTheme.surfaceWhite,
                  selectedIconTheme: const IconThemeData(color: AppTheme.secondaryBlue),
                  selectedLabelTextStyle: const TextStyle(color: AppTheme.secondaryBlue, fontWeight: FontWeight.bold),
                  unselectedIconTheme: const IconThemeData(color: AppTheme.textMuted),
                  unselectedLabelTextStyle: const TextStyle(color: AppTheme.textMuted),
                  destinations: const [
                    NavigationRailDestination(icon: Icon(Icons.folder_special), label: Text('Cases')),
                    NavigationRailDestination(icon: Icon(Icons.dashboard), label: Text('Dashboard')),
                    NavigationRailDestination(icon: Icon(Icons.source), label: Text('Evidence')),
                    NavigationRailDestination(icon: Icon(Icons.hub), label: Text('Topology')),
                    NavigationRailDestination(icon: Icon(Icons.smart_toy), label: Text('AI Agent')),
                  ],
                ),
                const VerticalDivider(thickness: 1, width: 1, color: AppTheme.borderLight),
                Expanded(child: child),
              ],
            );
          }
          return child;
        },
      ),
      bottomNavigationBar: isMobile
          ? NavigationBar(
              selectedIndex: currentIndex,
              onDestinationSelected: (idx) => _onItemTapped(idx, context),
              backgroundColor: AppTheme.surfaceWhite,
              indicatorColor: AppTheme.secondaryBlue.withOpacity(0.2),
              destinations: const [
                NavigationDestination(icon: Icon(Icons.folder_special), label: 'Cases'),
                NavigationDestination(icon: Icon(Icons.dashboard), label: 'Dash'),
                NavigationDestination(icon: Icon(Icons.source), label: 'Evidence'),
                NavigationDestination(icon: Icon(Icons.hub), label: 'Graph'),
                NavigationDestination(icon: Icon(Icons.smart_toy), label: 'Agent'),
              ],
            )
          : null,
    );
  }
}

// Widget that polls /health API to show live system status
class _SystemHealthWidget extends StatefulWidget {
  const _SystemHealthWidget();

  @override
  State<_SystemHealthWidget> createState() => _SystemHealthWidgetState();
}

class _SystemHealthWidgetState extends State<_SystemHealthWidget> {
  bool _isOnline = false;
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _checkHealth();
    // Poll every 15 seconds
    _timer = Timer.periodic(const Duration(seconds: 15), (_) => _checkHealth());
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _checkHealth() async {
    try {
      await apiService.checkHealth();
      if (!_isOnline) setState(() => _isOnline = true);
    } catch (_) {
      if (_isOnline) setState(() => _isOnline = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Hide text on mobile, just show the colored dot
    final isMobile = MediaQuery.of(context).size.width < 600;

    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: _isOnline ? AppTheme.accentTeal : AppTheme.dangerRed,
            boxShadow: [
              BoxShadow(
                color: _isOnline ? AppTheme.accentTeal.withOpacity(0.5) : AppTheme.dangerRed.withOpacity(0.5),
                blurRadius: 4,
                spreadRadius: 1,
              )
            ],
          ),
        ),
        if (!isMobile) ...[
          const SizedBox(width: 8),
          Text(
            _isOnline ? 'SYS: ONLINE' : 'SYS: OFFLINE',
            style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
              fontSize: 10,
              color: _isOnline ? AppTheme.textMuted : AppTheme.dangerRed,
            ),
          ),
        ]
      ],
    );
  }
}