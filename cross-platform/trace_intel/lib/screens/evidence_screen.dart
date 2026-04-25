import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/case_provider.dart';
import '../services/api_service.dart';
import '../theme/app_theme.dart';

class EvidenceScreen extends StatelessWidget {
  const EvidenceScreen({super.key});

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
          _buildHeader(selectedCase),
          SizedBox(height: isMobile ? 16 : 24),
          Expanded(child: _buildTabbedContent(selectedCase, isMobile)),
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
            const Icon(Icons.folder_off_outlined, size: 64, color: AppTheme.borderLight),
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
              'Select a target case from the Repository to browse raw evidence.',
              textAlign: TextAlign.center,
              style: AppTheme.lightTheme.textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(String caseId) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'INTELLIGENCE / RAW EVIDENCE / ${caseId.toUpperCase()}',
          style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(
            color: AppTheme.textMuted,
            fontSize: 10,
            letterSpacing: 1.5,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Evidence Browser',
          style: AppTheme.lightTheme.textTheme.displayLarge?.copyWith(
            fontSize: 24,
            color: AppTheme.primaryNavy,
          ),
        ),
      ],
    );
  }

  Widget _buildTabbedContent(String caseId, bool isMobile) {
    return DefaultTabController(
      length: 5, // Increased to 5 for Media Tab
      child: Container(
        decoration: BoxDecoration(
          color: AppTheme.surfaceWhite,
          border: Border.all(color: AppTheme.borderLight),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Column(
          children: [
            TabBar(
              isScrollable: isMobile,
              tabAlignment: isMobile ? TabAlignment.start : TabAlignment.center,
              labelColor: AppTheme.primaryNavy,
              unselectedLabelColor: AppTheme.textMuted,
              indicatorColor: AppTheme.secondaryBlue,
              indicatorWeight: 3,
              labelStyle: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12),
              tabs: const [
                Tab(icon: Icon(Icons.chat_bubble_outline, size: 20), text: 'Messages'),
                Tab(icon: Icon(Icons.phone_in_talk, size: 20), text: 'Calls'),
                Tab(icon: Icon(Icons.contacts_outlined, size: 20), text: 'Contacts'),
                Tab(icon: Icon(Icons.timeline, size: 20), text: 'Timeline'),
                Tab(icon: Icon(Icons.image_outlined, size: 20), text: 'Media'), // NEW
              ],
            ),
            const Divider(height: 1, color: AppTheme.borderLight),
            Expanded(
              child: TabBarView(
                children: [
                  _MessagesTab(caseId: caseId),
                  _CallsTab(caseId: caseId),
                  _ContactsTab(caseId: caseId),
                  _TimelineTab(caseId: caseId),
                  _MediaTab(caseId: caseId), // NEW
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ==========================================
// TAB 1: MESSAGES
// ==========================================
class _MessagesTab extends StatefulWidget {
  final String caseId;
  const _MessagesTab({required this.caseId});

  @override
  State<_MessagesTab> createState() => _MessagesTabState();
}

class _MessagesTabState extends State<_MessagesTab> with AutomaticKeepAliveClientMixin {
  late Future<List<dynamic>> _messagesFuture;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _messagesFuture = apiService.getMessages(widget.caseId);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return FutureBuilder<List<dynamic>>(
      future: _messagesFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
        if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: AppTheme.dangerRed)));
        if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('No communications found.', style: TextStyle(color: AppTheme.textMuted)));

        final messages = snapshot.data!;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: messages.length,
          separatorBuilder: (_, __) => const Divider(color: AppTheme.borderLight),
          itemBuilder: (context, index) {
            final msg = messages[index];
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const CircleAvatar(backgroundColor: AppTheme.bgLight, child: Icon(Icons.chat_bubble_outline, color: AppTheme.secondaryBlue, size: 18)),
              title: Text('${msg['sender']} → ${msg['receiver']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13, color: AppTheme.primaryNavy)),
              subtitle: Padding(padding: const EdgeInsets.only(top: 4.0), child: Text(msg['message'] ?? '', style: const TextStyle(color: AppTheme.textMain))),
              trailing: Text(msg['timestamp'] ?? '', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10, color: AppTheme.textMuted)),
            );
          },
        );
      },
    );
  }
}

// ==========================================
// TAB 2: CALL LOGS
// ==========================================
class _CallsTab extends StatefulWidget {
  final String caseId;
  const _CallsTab({required this.caseId});

  @override
  State<_CallsTab> createState() => _CallsTabState();
}

class _CallsTabState extends State<_CallsTab> with AutomaticKeepAliveClientMixin {
  late Future<List<dynamic>> _callsFuture;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _callsFuture = apiService.getCalls(widget.caseId);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return FutureBuilder<List<dynamic>>(
      future: _callsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
        if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: AppTheme.dangerRed)));
        if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('No call logs found.', style: TextStyle(color: AppTheme.textMuted)));

        final calls = snapshot.data!;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: calls.length,
          separatorBuilder: (_, __) => const Divider(color: AppTheme.borderLight),
          itemBuilder: (context, index) {
            final call = calls[index];
            final bool isIncoming = call['call_type'] == 'Incoming';
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: CircleAvatar(
                backgroundColor: isIncoming ? AppTheme.accentTeal.withOpacity(0.1) : AppTheme.secondaryBlue.withOpacity(0.1),
                child: Icon(isIncoming ? Icons.call_received : Icons.call_made, color: isIncoming ? AppTheme.accentTeal : AppTheme.secondaryBlue, size: 20),
              ),
              title: Text(isIncoming ? '${call['caller']} (Caller)' : '${call['receiver']} (Receiver)', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14, color: AppTheme.primaryNavy)),
              subtitle: Text('${call['duration']} sec • ${call['call_type']}', style: const TextStyle(color: AppTheme.textMuted, fontSize: 12)),
              trailing: Text(call['timestamp'] ?? '', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10, color: AppTheme.textMuted)),
            );
          },
        );
      },
    );
  }
}

// ==========================================
// TAB 3: CONTACTS
// ==========================================
class _ContactsTab extends StatefulWidget {
  final String caseId;
  const _ContactsTab({required this.caseId});

  @override
  State<_ContactsTab> createState() => _ContactsTabState();
}

class _ContactsTabState extends State<_ContactsTab> with AutomaticKeepAliveClientMixin {
  late Future<List<dynamic>> _contactsFuture;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _contactsFuture = apiService.getContacts(widget.caseId);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return FutureBuilder<List<dynamic>>(
      future: _contactsFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
        if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: AppTheme.dangerRed)));
        if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('No contacts found.', style: TextStyle(color: AppTheme.textMuted)));

        final contacts = snapshot.data!;
        return ListView.separated(
          padding: const EdgeInsets.all(16),
          itemCount: contacts.length,
          separatorBuilder: (_, __) => const Divider(color: AppTheme.borderLight),
          itemBuilder: (context, index) {
            final contact = contacts[index];
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: const CircleAvatar(backgroundColor: AppTheme.primaryNavy, child: Icon(Icons.person, color: Colors.white, size: 20)),
              title: Text(contact['name'] ?? 'Unknown', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
              subtitle: Text(contact['phone'] ?? '', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 12)),
            );
          },
        );
      },
    );
  }
}

// ==========================================
// TAB 4: EVENT TIMELINE
// ==========================================
class _TimelineTab extends StatefulWidget {
  final String caseId;
  const _TimelineTab({required this.caseId});

  @override
  State<_TimelineTab> createState() => _TimelineTabState();
}

class _TimelineTabState extends State<_TimelineTab> with AutomaticKeepAliveClientMixin {
  late Future<List<dynamic>> _timelineFuture;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _timelineFuture = apiService.getTimeline(widget.caseId);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return FutureBuilder<List<dynamic>>(
      future: _timelineFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
        if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: AppTheme.dangerRed)));
        if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('No timeline events found.', style: TextStyle(color: AppTheme.textMuted)));

        final events = snapshot.data!;
        return ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: events.length,
          itemBuilder: (context, index) {
            final event = events[index];
            return Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Column(
                  children: [
                    Container(width: 12, height: 12, decoration: const BoxDecoration(color: AppTheme.secondaryBlue, shape: BoxShape.circle)),
                    if (index != events.length - 1) Container(width: 2, height: 60, color: AppTheme.borderLight),
                  ],
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 24.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(event['timestamp'] ?? '', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 10, color: AppTheme.textMuted)),
                        const SizedBox(height: 4),
                        Wrap(
                          crossAxisAlignment: WrapCrossAlignment.center,
                          spacing: 8,
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(color: AppTheme.bgLight, borderRadius: BorderRadius.circular(4)),
                              child: Text(event['event_type']?.toUpperCase() ?? 'EVENT', style: AppTheme.lightTheme.textTheme.labelLarge?.copyWith(fontSize: 9, color: AppTheme.primaryNavy)),
                            ),
                            Text(event['user_name'] ?? '', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13)),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(event['details'] ?? '', style: const TextStyle(color: AppTheme.textMain)),
                      ],
                    ),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }
}

// ==========================================
// NEW TAB 5: MEDIA GALLERY (With Hero Animation)
// ==========================================
class _MediaTab extends StatefulWidget {
  final String caseId;
  const _MediaTab({required this.caseId});

  @override
  State<_MediaTab> createState() => _MediaTabState();
}

class _MediaTabState extends State<_MediaTab> with AutomaticKeepAliveClientMixin {
  late Future<List<dynamic>> _mediaFuture;

  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _mediaFuture = apiService.getMedia(widget.caseId);
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return FutureBuilder<List<dynamic>>(
      future: _mediaFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: AppTheme.primaryNavy));
        if (snapshot.hasError) return Center(child: Text('Error: ${snapshot.error}', style: const TextStyle(color: AppTheme.dangerRed)));
        if (!snapshot.hasData || snapshot.data!.isEmpty) return const Center(child: Text('No media assets found.', style: TextStyle(color: AppTheme.textMuted)));

        final mediaList = snapshot.data!;
        return GridView.builder(
          padding: const EdgeInsets.all(16),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
            maxCrossAxisExtent: 150,
            crossAxisSpacing: 8,
            mainAxisSpacing: 8,
          ),
          itemCount: mediaList.length,
          itemBuilder: (context, index) {
            final media = mediaList[index];
            final fileName = media['file_name'] ?? '';
            final imageUrl = apiService.getMediaUrl(widget.caseId, fileName);

            return InkWell(
              onTap: () => _openFullscreenImage(context, imageUrl, fileName),
              child: Hero(
                tag: imageUrl, // Beautiful layout animation
                child: Container(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(8),
                    color: AppTheme.bgLight,
                    border: Border.all(color: AppTheme.borderLight),
                    image: DecorationImage(
                      image: NetworkImage(imageUrl),
                      fit: BoxFit.cover,
                      // Fallback if the backend doesn't actually have the file
                      onError: (exception, stackTrace) {},
                    ),
                  ),
                  child: Align(
                    alignment: Alignment.bottomCenter,
                    child: Container(
                      width: double.infinity,
                      color: Colors.black54,
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Text(
                        fileName,
                        textAlign: TextAlign.center,
                        style: const TextStyle(color: Colors.white, fontSize: 10),
                      ),
                    ),
                  ),
                ),
              ),
            );
          },
        );
      },
    );
  }

  void _openFullscreenImage(BuildContext context, String imageUrl, String fileName) {
    Navigator.push(context, MaterialPageRoute(
      builder: (ctx) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          backgroundColor: Colors.black,
          iconTheme: const IconThemeData(color: Colors.white),
          title: Text(fileName, style: const TextStyle(color: Colors.white, fontSize: 14)),
        ),
        body: Center(
          child: InteractiveViewer( // Allows pinching to zoom in on the image!
            panEnabled: true,
            child: Hero(
              tag: imageUrl,
              child: Image.network(imageUrl, fit: BoxFit.contain),
            ),
          ),
        ),
      ),
    ));
  }
}