// $Id$
/* Copyright (c) 2001 The Regents of the University of California through
   E.O. Lawrence Berkeley National Laboratory, subject to approval by the
   U.S. Department of Energy. See files COPYRIGHT.txt and
   cctbx/LICENSE.txt for further details.

   Revision history:
     2001 Nov 03: fftbx started, based on fftpack41 (rwgk)
 */

#ifndef CCTBX_FFTBX_FACTORIZATION_H
#define CCTBX_FFTBX_FACTORIZATION_H

#include <vector>
#include <boost/array.hpp>

namespace cctbx { namespace fftbx {

  /*! \brief Determination of prime factors for both complex-to-complex
       and real-to-complex transforms.
   */
  class factorization
  {
    public:
      //! Default constructor.
      factorization() : m_N(0) {}
      //! Determination of the %factorization of N.
      /*! Computation of the prime factors of N with the specialization
          that one length-4 transform is computed instead of two length-2
          transforms.
       */
      factorization(std::size_t N, bool real_to_complex);
      //! Access the N that was passed to the constructor.
      std::size_t N() const { return m_N; }
      //! Access the factors of N.
      const std::vector<std::size_t>& Factors() const {
        return m_Factors;
      }
    protected:
      std::size_t m_N;
      std::vector<std::size_t> m_Factors;
  };

  namespace detail {

    inline std::size_t
    CountReduce(std::size_t& RedN, const std::size_t& factor)
    {
      std::size_t result = 0;
      while (RedN % factor == 0) {
        RedN /= factor;
        result++;
      }
      return result;
    }

  } // namespace detail

  inline // Potential NOINLINE
  factorization::factorization(std::size_t N, bool real_to_complex)
    : m_N(N)
  {
    // Based on the first parts of FFTPACK41 cffti1.f and rffti1.f.
    const boost::array<std::size_t, 3> OptFactors = {3, 4, 2};
    boost::array<std::size_t, 3> Perm = {2, 0, 1};
    if (real_to_complex) { // XXX does this make a difference?
      Perm[1] = 1;
      Perm[2] = 0;
    }
    boost::array<std::size_t, 3> Count;
    Count.assign(0);
    std::size_t RedN = m_N;
    std::size_t i;
    for (i = 0; RedN > 1 && i < OptFactors.size(); i++) {
      Count[i] = detail::CountReduce(RedN, OptFactors[i]);
    }
    for (i = 0; i < OptFactors.size(); i++) {
      m_Factors.insert(m_Factors.end(), Count[Perm[i]], OptFactors[Perm[i]]);
    }
    for (std::size_t factor = 5; RedN > 1; factor += 2) {
      m_Factors.insert(
        m_Factors.end(), detail::CountReduce(RedN, factor), factor);
    }
  }

}} // namespace cctbx::fftbx

#endif // CCTBX_FFTBX_FACTORIZATION_H
