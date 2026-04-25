import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart'; // IMPORT DOTENV

import 'theme/app_theme.dart';
import 'providers/case_provider.dart';

import 'screens/main_layout.dart';
import 'screens/dashboard_screen.dart';
import 'screens/investigation_screen.dart';
import 'screens/case_explorer_screen.dart';
import 'screens/evidence_screen.dart';
import 'screens/network_graph_screen.dart';

// Change main to async so we can await the environment variables
Future<void> main() async {
  // Ensure Flutter engine is initialized before loading files
  WidgetsFlutterBinding.ensureInitialized();
  
  // Load the .env file
  await dotenv.load(fileName: ".env");

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => CaseProvider()),
      ],
      child: const TraceIntelApp(),
    ),
  );
}

class TraceIntelApp extends StatelessWidget {
  const TraceIntelApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'TraceIntel',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      routerConfig: _router,
    );
  }
}

final GoRouter _router = GoRouter(
  initialLocation: '/cases',
  routes: [
    ShellRoute(
      builder: (context, state, child) {
        return MainLayout(child: child);
      },
      routes: [
        GoRoute(
          path: '/cases',
          builder: (context, state) => const CaseExplorerScreen(),
        ),
        GoRoute(
          path: '/dashboard',
          builder: (context, state) => const DashboardScreen(),
        ),
        GoRoute(
          path: '/evidence',
          builder: (context, state) => const EvidenceScreen(),
        ),
        GoRoute(
          path: '/graph',
          builder: (context, state) => const NetworkGraphScreen(),
        ),
        GoRoute(
          path: '/investigation',
          builder: (context, state) => const InvestigationScreen(),
        ),
      ],
    ),
  ],
);