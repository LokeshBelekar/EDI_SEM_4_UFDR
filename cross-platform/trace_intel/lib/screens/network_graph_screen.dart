import 'dart:math';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class NetworkGraphScreen extends StatefulWidget {
  const NetworkGraphScreen({super.key});

  @override
  State<NetworkGraphScreen> createState() => _NetworkGraphScreenState();
}

class _NetworkGraphScreenState extends State<NetworkGraphScreen> {
  Map<String, dynamic>? _graphData;
  bool _isLoading = false;
  String? _error;
  
  // Pre-calculated node positions for the interactive Stack
  final Map<String, Offset> _nodePositions = {};
  final double _canvasSize = 3000.0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final selectedCase = context.watch<CaseProvider>().selectedCase;
    if (selectedCase != null && _graphData == null && !_isLoading) {
      _fetchGraph(selectedCase);
    }
  }

  Future<void> _fetchGraph(String caseId) async {
    setState(() {
      _isLoading = true;
      _error = null;
    });

    try {
      final data = await apiService.getNetworkGraph(caseId);
      _calculateLayout(data['nodes'] ?? []);
      setState(() {
        _graphData = data;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _error = "GRAPH_COMPUTATION_FAILURE: Unable to generate topology.";
        _isLoading = false;
      });
    }
  }

  // Calculates a circular layout for the nodes
  void _calculateLayout(List<dynamic> nodes) {
    _nodePositions.clear();
    final center = Offset(_canvasSize / 2, _canvasSize / 2);
    final radius = _canvasSize / 3;

    int totalNodes = nodes.length;
    if (totalNodes == 0) return;

    // Group by community to keep related nodes close
    Map<String, List<dynamic>> communities = {};
    for (var node in nodes) {
      final comm = node['community'] ?? 'Unknown';
      communities.putIfAbsent(comm, () => []).add(node);
    }

    double angleStep = (2 * pi) / totalNodes;
    double currentAngle = 0;

    for (var comm in communities.values) {
      for (var node in comm) {
        final double x = center.dx + radius * cos(currentAngle);
        final double y = center.dy + radius * sin(currentAngle);
        _nodePositions[node['id']] = Offset(x, y);
        currentAngle += angleStep;
      }
    }
  }

  // The new interactive Bottom Sheet!
  void _showNodeDetails(Map<String, dynamic> node) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppTheme.surfaceWhite,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const CircleAvatar(
                    backgroundColor: AppTheme.primaryNavy,
                    radius: 24,
                    child: Icon(Icons.person, color: Colors.white),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          node['label'] ?? node['id'], 
                          style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: AppTheme.primaryNavy)
                        ),
                        Text(
                          'Community: ${node['community'] ?? 'Unknown'}', 
                          style: const TextStyle(color: AppTheme.secondaryBlue, fontWeight: FontWeight.w600)
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              const Text('FORENSIC METRICS', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: AppTheme.textMuted)),
              const Divider(),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.hub, color: AppTheme.accentTeal),
                title: const Text('Betweenness Centrality', style: TextStyle(fontSize: 14)),
                trailing: Text((node['betweenness']?.toStringAsFixed(4) ?? '0.0000'), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.share, color: AppTheme.secondaryBlue),
                title: const Text('PageRank Influence', style: TextStyle(fontSize: 14)),
                trailing: Text((node['pagerank']?.toStringAsFixed(4) ?? '0.0000'), style: const TextStyle(fontWeight: FontWeight.bold)),
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primaryNavy, 
                    padding: const EdgeInsets.all(16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                  ),
                  onPressed: () => Navigator.pop(ctx),
                  child: const Text('CLOSE DOSSIER', style: TextStyle(color: Colors.white, letterSpacing: 1)),
                ),
              )
            ],
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final selectedCase = context.watch<CaseProvider>().selectedCase;

    if (selectedCase == null) {
      return const Center(child: Text("Awaiting Case Context", style: TextStyle(fontSize: 24, color: AppTheme.primaryNavy)));
    }

    return Padding(
      padding: const EdgeInsets.all(32.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(selectedCase),
          const SizedBox(height: 24),
          Expanded(child: _buildGraphArea()),
        ],
      ),
    );
  }

  Widget _buildHeader(String caseId) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'INTELLIGENCE / TOPOLOGY / ${caseId.toUpperCase()}',
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMuted,
            fontSize: 12,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Network Topology',
          style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
            fontSize: 28,
            color: AppTheme.primaryNavy,
          ),
        ),
      ],
    );
  }

  Widget _buildGraphArea() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
    }

    if (_error != null) {
      return Center(child: Text(_error!, style: const TextStyle(color: AppTheme.dangerRed)));
    }

    if (_graphData == null || _graphData!['nodes'].isEmpty) {
      return const Center(child: Text("No relational data found to build graph."));
    }

    final edges = List<Map<String, dynamic>>.from(_graphData!['edges']);
    final nodes = List<Map<String, dynamic>>.from(_graphData!['nodes']);

    return Container(
      decoration: BoxDecoration(
        color: AppTheme.surfaceWhite,
        border: Border.all(color: AppTheme.borderLight),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Stack(
        children: [
          // The massive zoomable area
          InteractiveViewer(
            constrained: false,
            boundaryMargin: const EdgeInsets.all(2000),
            minScale: 0.05,
            maxScale: 3.0,
            child: SizedBox(
              width: _canvasSize,
              height: _canvasSize,
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  // Layer 1: Edges (CustomPaint)
                  Positioned.fill(
                    child: CustomPaint(
                      painter: _EdgePainter(edges: edges, nodePositions: _nodePositions),
                    ),
                  ),
                  // Layer 2: Interactive Nodes (Widgets)
                  ...nodes.map((node) {
                    final pos = _nodePositions[node['id']];
                    if (pos == null) return const SizedBox.shrink();

                    final pagerank = (node['pagerank'] as num?)?.toDouble() ?? 0.0;
                    final isHighRisk = pagerank > 0.05;

                    return Positioned(
                      left: pos.dx - 30, // Offset by half width to center on the line
                      top: pos.dy - 30,
                      child: GestureDetector(
                        onTap: () => _showNodeDetails(node),
                        child: Column(
                          children: [
                            Container(
                              width: 60,
                              height: 60,
                              decoration: BoxDecoration(
                                color: isHighRisk ? AppTheme.dangerRed : AppTheme.primaryNavy,
                                shape: BoxShape.circle,
                                border: Border.all(color: Colors.white, width: 3),
                                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 8, spreadRadius: 1)],
                              ),
                              child: const Icon(Icons.person, color: Colors.white, size: 28),
                            ),
                            const SizedBox(height: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.95),
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(color: AppTheme.borderLight),
                              ),
                              child: Text(
                                node['label'] ?? node['id'],
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                              ),
                            ),
                          ],
                        ),
                      ),
                    );
                  }),
                ],
              ),
            ),
          ),
          // Legend
          Positioned(
            top: 24,
            left: 24,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: Colors.white.withOpacity(0.9),
                border: Border.all(color: AppTheme.borderLight),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('TOPOLOGY LEGEND', style: AppTheme.lightTheme.textTheme.labelLarge),
                  const SizedBox(height: 8),
                  _buildLegendItem(AppTheme.primaryNavy, 'Standard Node'),
                  _buildLegendItem(AppTheme.dangerRed, 'High Centrality (Hub)'),
                  const SizedBox(height: 8),
                  const Text('Interaction: Tap nodes for details', style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic)),
                ],
              ),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4.0),
      child: Row(
        children: [
          Container(width: 12, height: 12, decoration: BoxDecoration(color: color, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Text(text, style: const TextStyle(fontSize: 12, color: AppTheme.textMain)),
        ],
      ),
    );
  }
}

// --- Edge Rendering Engine with Text Labels ---
class _EdgePainter extends CustomPainter {
  final List<Map<String, dynamic>> edges;
  final Map<String, Offset> nodePositions;

  _EdgePainter({required this.edges, required this.nodePositions});

  @override
  void paint(Canvas canvas, Size size) {
    final edgePaint = Paint()
      ..color = AppTheme.secondaryBlue.withOpacity(0.4)
      ..style = PaintingStyle.stroke;

    for (var edge in edges) {
      final sourcePos = nodePositions[edge['source']];
      final targetPos = nodePositions[edge['target']];
      
      if (sourcePos != null && targetPos != null) {
        // Highlight edge thickness based on weight
        final weight = (edge['weight'] as num?)?.toDouble() ?? 1.0;
        edgePaint.strokeWidth = min(weight, 5.0);
        
        // Draw the connection line
        canvas.drawLine(sourcePos, targetPos, edgePaint);

        // Draw the Text Label exactly in the middle of the line
        final midX = (sourcePos.dx + targetPos.dx) / 2;
        final midY = (sourcePos.dy + targetPos.dy) / 2;

        final relType = edge['type'] ?? 'LINK';
        
        final textSpan = TextSpan(
          text: ' $relType ($weight) ',
          style: TextStyle(
            color: AppTheme.primaryNavy, 
            fontSize: 10, 
            fontWeight: FontWeight.bold, 
            backgroundColor: Colors.white.withOpacity(0.8) // Creates a background so the text is readable over the line
          ),
        );
        final textPainter = TextPainter(text: textSpan, textDirection: TextDirection.ltr);
        textPainter.layout();
        
        // Offset by half the text width/height to center it perfectly on the midpoint
        textPainter.paint(canvas, Offset(midX - (textPainter.width / 2), midY - (textPainter.height / 2)));
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}