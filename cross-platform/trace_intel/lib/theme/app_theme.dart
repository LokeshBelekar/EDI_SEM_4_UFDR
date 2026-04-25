import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Professional, lighter color palette for TraceIntel
  static const Color primaryNavy = Color(0xFF1A365D);
  static const Color secondaryBlue = Color(0xFF3182CE);
  static const Color accentTeal = Color(0xFF38B2AC);
  static const Color dangerRed = Color(0xFFE53E3E);
  
  static const Color bgLight = Color(0xFFF7FAFC);
  static const Color surfaceWhite = Color(0xFFFFFFFF);
  
  static const Color textMain = Color(0xFF2D3748);
  static const Color textMuted = Color(0xFF718096);
  static const Color borderLight = Color(0xFFE2E8F0);

  static ThemeData get lightTheme {
    return ThemeData(
      scaffoldBackgroundColor: bgLight,
      primaryColor: primaryNavy,
      colorScheme: const ColorScheme.light(
        primary: primaryNavy,
        secondary: secondaryBlue,
        surface: surfaceWhite,
        error: dangerRed,
      ),
      textTheme: GoogleFonts.interTextTheme().copyWith(
        displayLarge: GoogleFonts.inter(color: textMain, fontWeight: FontWeight.bold),
        bodyLarge: GoogleFonts.inter(color: textMain),
        bodyMedium: GoogleFonts.inter(color: textMuted),
        labelLarge: GoogleFonts.ibmPlexMono(fontWeight: FontWeight.w600), // For terminal/monospaced text
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceWhite,
        foregroundColor: primaryNavy,
        elevation: 1,
        shadowColor: borderLight,
      ),
      cardTheme: CardThemeData( // Changed CardTheme to CardThemeData here!
        color: surfaceWhite,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: const BorderSide(color: borderLight),
        ),
      ),
    );
  }
}